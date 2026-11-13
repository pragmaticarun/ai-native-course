"""P8 milestones 1, 3, 4: the agent as an explicit, checkpointed graph.

    observe -> plan -> guard (interrupt for a human) -> act -> verify -+-> plan ...
                ^                                                  +-> recover -> observe
                +-- budgets (steps, time, cost) end the run here, not in a prompt

The env, model and adapter are closed over; everything in the state is plain data, so the
checkpointer can resume a run after the environment crashes.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from p8_adapters import ADAPTERS, AdapterError, Decoded
from p8_guard import injection_flags, review
from p8_kit import Action, Env, Model, Obs, estimate_tokens


@dataclass(frozen=True)
class Budget:
    max_steps: int = 14
    max_seconds: float = 120.0
    max_usd: float = 0.50  # with the placeholder price


class State(TypedDict, total=False):
    goal: str
    step: int
    status: str
    answer: str
    obs: dict[str, Any]
    note: str
    feedback: Any
    pending: list[dict[str, Any]]
    approved: int
    outcomes: list[list[Any]]
    invalid: int
    blocked: list[str]
    interventions: int
    flags: list[str]
    tokens: int
    started: float
    fails_in_row: int
    recoveries: list[str]
    log: list[str]


def _decoded(pending: list[dict[str, Any]]) -> Decoded:
    return Decoded([(p["ref"], Action.from_dict(p["action"])) for p in pending])


def build(
    env: Env, model: Model, adapter_name: str, budget: Budget, checkpointer: Any = None
) -> Any:
    adapter = ADAPTERS[adapter_name]

    def observe(s: State) -> State:
        obs = env.observe()
        obs.note = s.get("note", "")
        flags = sorted(set(s.get("flags", [])) | set(injection_flags(obs.text)))
        return {"obs": obs.to_dict(), "flags": flags, "started": s.get("started") or time.time()}

    def plan(s: State) -> State:
        step, tokens = s.get("step", 0), s.get("tokens", 0)
        # TODO(milestone 4): enforce the budget here, in the graph: end the run with status
        # "out_of_steps", "out_of_time" or "out_of_budget" (tokens * USD_PER_1K_TOKENS / 1000).
        obs = Obs.from_dict(s["obs"])
        turn = model.next(obs, s.get("feedback"))
        tokens += estimate_tokens(obs, adapter.pixel)
        if turn.get("replay_exhausted"):
            return {"status": "replay_exhausted", "tokens": tokens}
        try:
            d = adapter.decode(turn)
        except AdapterError as e:
            return {
                "pending": [],
                "note": f"invalid: {e}",
                "invalid": s.get("invalid", 0) + 1,
                "tokens": tokens,
                "step": step + 1,
            }
        if d.done:
            return {"status": "done", "answer": d.answer, "tokens": tokens}
        pending = [{"ref": r, "action": a.to_dict()} for r, a in d.actions]
        return {"pending": pending, "tokens": tokens}

    def guard(s: State) -> State:
        obs = Obs.from_dict(s["obs"])
        blocked, asked, note = list(s.get("blocked", [])), 0, ""
        approved = 0
        for p in s["pending"]:
            a = Action.from_dict(p["action"])
            v = review(a, env.describe(a, obs), s["goal"], obs.text)
            if v.decision == "ask":
                asked += 1
                if not interrupt({"action": p["action"], "reason": v.reason}):
                    note = f"denied by human: {v.reason}"
                    break
            elif v.decision == "block":
                blocked.append(v.reason)
                note = f"blocked: {v.reason}"
                break
            approved += 1
        return {
            "approved": approved,
            "blocked": blocked,
            "interventions": s.get("interventions", 0) + asked,
            "note": note,
        }

    def act(s: State) -> State:
        obs = Obs.from_dict(s["obs"])
        outcomes: list[list[Any]] = []
        for p in s["pending"][: s["approved"]]:
            ok, msg = env.execute(Action.from_dict(p["action"]), obs)
            outcomes.append([ok, msg])
            if not ok:
                break
        bad = [m for ok, m in outcomes if not ok]
        return {
            "outcomes": outcomes,
            "invalid": s.get("invalid", 0) + len(bad),
            "note": bad[0] if bad else s.get("note", ""),
        }

    def verify(s: State) -> State:
        before = s["obs"]["frame"]
        obs = env.observe()
        obs.note = s.get("note", "")
        outcomes = [tuple(o) for o in s.get("outcomes", [])]
        effective = any(
            Action.from_dict(p["action"]).kind in ("click", "type", "key") for p in s["pending"]
        )
        failed = bool(s.get("note")) or (effective and obs.frame == before)
        feedback = (
            adapter.results(_decoded(s["pending"]), outcomes, f"<png sha256 {obs.frame}>")
            if s["pending"]
            else None
        )
        log = [
            *s.get("log", []),
            f"{s.get('step', 0)}: {len(outcomes)}/{len(s['pending'])} ran; {obs.note or 'ok'}",
        ]
        return {
            "obs": obs.to_dict(),
            "feedback": feedback,
            "step": s.get("step", 0) + 1,
            "log": log,
            "fails_in_row": s.get("fails_in_row", 0) + 1 if failed else 0,
            "outcomes": [],
            "flags": sorted(set(s.get("flags", [])) | set(injection_flags(obs.text))),
        }

    def recover(s: State) -> State:
        rec = [*s.get("recoveries", []), env.recover(len(s.get("recoveries", [])))]
        return {"recoveries": rec, "fails_in_row": 0, "note": "recovered: " + rec[-1]}

    def after_plan(s: State) -> str:
        if s.get("status"):
            return END
        return "guard" if s.get("pending") else "observe"

    g: Any = StateGraph(
        State
    )  # langgraph 1.2.21's add_node overloads reject TypedDict nodes under mypy
    for name, fn in [
        ("observe", observe),
        ("plan", plan),
        ("guard", guard),
        ("act", act),
        ("verify", verify),
        ("recover", recover),
    ]:
        g.add_node(name, fn)
    g.add_edge(START, "observe")
    g.add_edge("observe", "plan")
    g.add_conditional_edges("plan", after_plan, ["guard", "observe", END])
    g.add_edge("guard", "act")
    g.add_edge("act", "verify")
    # TODO(milestone 4): after two failed steps in a row, route to "recover" instead.
    g.add_conditional_edges("verify", lambda s: "plan", ["recover", "plan"])
    g.add_edge("recover", "observe")
    return g.compile(checkpointer=checkpointer or InMemorySaver())


def drive(
    graph: Any, goal: str, thread: str, human: str | None, resume: bool = False
) -> tuple[State, int]:
    """Run to the end, answering each `interrupt` with the task's human policy (default: deny).
    Returns the final state and how many times the human was asked."""
    cfg = {"configurable": {"thread_id": thread}, "recursion_limit": 400}
    asked = 0
    out = graph.invoke(None if resume else {"goal": goal}, cfg)
    while graph.get_state(cfg).interrupts:
        asked += 1
        out = graph.invoke(Command(resume=human == "approve"), cfg)
    return out, asked
