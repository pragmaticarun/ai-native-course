"""M7 worked example: the M3 computer-use loop as an explicit LangGraph.

    observe -> plan -> guard -> act -> verify -> observe ...
                  \\-> done      \\-> (interrupt for consequential actions)
                                         verify -> recover -> observe | gave_up

* observe: screenshot text (what a vision model would read) plus an accessibility snapshot
  (focus, values) from the environment;
* plan: picks ONE action, using coordinates from the screenshot text (which can be stale);
* guard: M5's policy check; consequential targets (submit, pay, delete...) `interrupt` for a
  human, and screen text that looks like instructions is flagged in the payload;
* act: runs the action with a `RetryPolicy` for transient adb/emulator errors;
* verify: checks the state diff the action should have caused; a miss goes to `recover`.

The checkpointer saves state after every node, so if the emulator crashes mid-run the
graph resumes from the last completed node (`graph.invoke(None, config)`) instead of
starting again. Runs against the M3 simulator only: the emulator/A73 path is untested.
"""

from __future__ import annotations

import operator
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, RetryPolicy, interrupt

HERE = Path(__file__).resolve().parent
for sibling in ("m3", "m5"):
    sys.path.insert(0, str(HERE.parent / sibling))

from computer_use_sim import Action, FormScreen, _find  # noqa: E402
from gui_safety import classify, untrusted_text_flags  # noqa: E402


class TransientADBError(Exception):
    """e.g. `adb: device offline` for a moment. Safe to retry."""


class EmulatorCrashed(Exception):
    """The emulator process died. Not retried in-node: restart it, then resume the graph."""


@dataclass
class Emulator:
    """Wraps the simulated screen with the failure modes of a real device."""

    screen: FormScreen
    transient_at: set[int] = field(default_factory=set)  # action numbers that fail once
    crash_at: int | None = None  # action number that crashes the emulator once
    actions: int = 0
    attempts: int = 0
    banner: str = ""  # untrusted text drawn on screen (e.g. a notification)

    def screenshot(self) -> str:
        shot = self.screen.screenshot()
        return f"{shot}; banner={self.banner!r}" if self.banner else shot

    def a11y(self) -> dict[str, Any]:
        s = self.screen
        return {"focused": s.focused, "values": dict(s.values), "submitted": s.submitted}

    def apply(self, action: Action) -> None:
        self.attempts += 1
        number = self.actions + 1
        if number in self.transient_at:
            self.transient_at.discard(number)
            raise TransientADBError(f"device offline during action {number}")
        if self.crash_at == number:
            self.crash_at = None
            raise EmulatorCrashed(f"emulator died during action {number}")
        self.screen.apply(action)
        self.actions = number


ENVIRONMENTS: dict[str, Emulator] = {}  # thread_id -> device; the device is outside the graph


class GuiState(TypedDict, total=False):
    thread: str
    name: str
    email: str
    obs: str
    a11y: dict[str, Any]
    pending: dict[str, Any]
    expect: dict[str, Any]
    steps: int
    recoveries: int
    status: str
    log: Annotated[list[str], operator.add]


def observe(state: GuiState) -> GuiState:
    env = ENVIRONMENTS[state["thread"]]
    return {"obs": env.screenshot(), "a11y": env.a11y()}


def plan(state: GuiState) -> GuiState:
    a, obs = state["a11y"], state["obs"]
    values = a["values"]
    if (
        a["submitted"]
        and values.get("name_field") == state["name"]
        and values.get("email_field") == state["email"]
    ):
        return {"status": "done", "pending": {}}
    if state.get("steps", 0) >= 12:
        return {"status": "gave_up", "pending": {}}
    for target, wanted in (("name_field", state["name"]), ("email_field", state["email"])):
        if values.get(target) != wanted:
            if a["focused"] == target:
                pending: dict[str, Any] = {"kind": "type", "text": wanted, "target": target}
                return {"pending": pending, "expect": {"value": (target, wanted)}}
            x, y = _find(obs, target)  # from the screenshot: may be stale
            pending = {"kind": "click", "x": x, "y": y, "target": target}
            return {"pending": pending, "expect": {"focused": target}}
    x, y = _find(obs, "submit_button")
    pending = {"kind": "click", "x": x, "y": y, "target": "submit_button"}
    return {"pending": pending, "expect": {"submitted": True}}


def after_plan(state: GuiState) -> str:
    return END if state.get("status") in {"done", "gave_up"} else "guard"


def guard(state: GuiState) -> Command:
    action = state["pending"]
    if classify(action["target"]) == "consequential":
        flags = untrusted_text_flags(state["obs"])
        answer = interrupt({"action": action, "screen": state["obs"], "untrusted_text": flags})
        if answer != "approve":
            return Command(
                goto=END,
                update={"status": "rejected", "log": [f"human rejected {action['target']}"]},
            )
        return Command(goto="act", update={"log": [f"human approved {action['target']}"]})
    return Command(goto="act")


def act(state: GuiState) -> GuiState:
    p = state["pending"]
    action = (
        Action("click", p["x"], p["y"]) if p["kind"] == "click" else Action("type", text=p["text"])
    )
    ENVIRONMENTS[state["thread"]].apply(action)
    return {"steps": state.get("steps", 0) + 1, "log": [f"{p['kind']} {p['target']}"]}


def verify(state: GuiState) -> Command:
    now = ENVIRONMENTS[state["thread"]].a11y()
    exp = state["expect"]
    ok = (
        ("focused" not in exp or now["focused"] == exp["focused"])
        and ("submitted" not in exp or now["submitted"] is True)
        and ("value" not in exp or now["values"].get(exp["value"][0]) == exp["value"][1])
    )
    return Command(goto="observe" if ok else "recover")


def recover(state: GuiState) -> Command:
    n = state.get("recoveries", 0) + 1
    if n > 3:
        return Command(goto=END, update={"recoveries": n, "status": "gave_up"})
    return Command(goto="observe", update={"recoveries": n, "log": [f"recover #{n}: re-observe"]})


ACT_RETRY = RetryPolicy(
    max_attempts=3, initial_interval=0.01, jitter=True, retry_on=TransientADBError
)


def build(checkpointer=None):
    g = StateGraph(GuiState)
    g.add_node("observe", observe)
    g.add_node("plan", plan)
    g.add_node("guard", guard, destinations=("act", END))
    g.add_node("act", act, retry_policy=ACT_RETRY)
    g.add_node("verify", verify, destinations=("observe", "recover"))
    g.add_node("recover", recover, destinations=("observe", END))
    g.add_edge(START, "observe")
    g.add_edge("observe", "plan")
    g.add_conditional_edges("plan", after_plan, ["guard", END])
    g.add_edge("act", "verify")
    return g.compile(checkpointer=checkpointer or InMemorySaver())


def start(graph, thread: str, env: Emulator, name: str, email: str) -> dict[str, Any]:
    ENVIRONMENTS[thread] = env
    cfg = {"configurable": {"thread_id": thread}, "recursion_limit": 100}
    return graph.invoke({"thread": thread, "name": name, "email": email, "log": []}, cfg)


def resume(graph, thread: str, value: Any = None) -> dict[str, Any]:
    cfg = {"configurable": {"thread_id": thread}, "recursion_limit": 100}
    return graph.invoke(Command(resume=value) if value is not None else None, cfg)


if __name__ == "__main__":
    graph = build()
    env = Emulator(FormScreen(layout_shift=True), transient_at={2}, crash_at=4)
    try:
        start(graph, "run-1", env, "Arun", "arun@example.com")
    except EmulatorCrashed as exc:
        cfg = {"configurable": {"thread_id": "run-1"}}
        print(f"crash: {exc}; checkpoint says next node = {graph.get_state(cfg).next}")
    out = resume(graph, "run-1")  # emulator restarted; continue from the checkpoint
    print("paused for a human:", out["__interrupt__"][0].value["action"])
    out = resume(graph, "run-1", "approve")
    print(out["status"], "| steps:", out["steps"], "| recoveries:", out.get("recoveries", 0))
    print("\n".join(out["log"]))
    print("device actions:", env.actions, "attempts:", env.attempts)
