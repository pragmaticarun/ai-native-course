"""L3 worked example (preview of M15): screenshot -> decide -> act -> observe.

To stay offline and deterministic, the "screen" is a simulated form, and a
"screenshot" is a text description of what is visible with pixel boxes (what a
vision model would extract). The real-browser version (Playwright) arrives in
M15; this file teaches the loop, the vendor-neutral action schema, and the two
vendor adapters:

* Anthropic `computer_toolset_20260801`: member `tool_use` blocks such as
  {"name": "left_click", "toolset_name": "computer", "input": {"coordinate": [x, y]}}
* OpenAI Responses `computer` tool: a `computer_call` with ordered `actions`
  such as {"type": "click", "button": "left", "x": 1, "y": 2} or {"type": "type", "text": ...}

Formats follow the vendors' docs as read on 13 Nov 2026. The adapters are
tested here against recorded payloads only; they have NOT been run against
the live APIs.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

# ----------------------------------------------------------------------------- actions


@dataclass(frozen=True)
class Action:
    kind: Literal["screenshot", "click", "type", "key", "done"]
    x: int = 0
    y: int = 0
    text: str = ""


def from_anthropic(block: dict[str, Any]) -> Action:
    """Translate one Anthropic computer-toolset `tool_use` block."""
    if block.get("toolset_name") != "computer":
        raise ValueError("not a computer toolset call")
    name, args = block["name"], block.get("input", {})
    if name == "screenshot":
        return Action("screenshot")
    if name == "left_click":
        x, y = args["coordinate"]
        return Action("click", x, y)
    if name == "type":
        return Action("type", text=args["text"])
    if name == "key":
        return Action("key", text=args["text"])
    raise ValueError(f"member {name!r} not supported by this simulator")


def from_openai(action: dict[str, Any]) -> Action:
    """Translate one action from an OpenAI `computer_call.actions` list."""
    kind = action["type"]
    if kind == "screenshot":
        return Action("screenshot")
    if kind == "click" and action.get("button", "left") == "left":
        return Action("click", int(action["x"]), int(action["y"]))
    if kind == "type":
        return Action("type", text=action["text"])
    if kind == "keypress":
        return Action("key", text="+".join(action["keys"]))
    raise ValueError(f"action {kind!r} not supported by this simulator")


# ----------------------------------------------------------------------------- environment


@dataclass
class Element:
    name: str
    x: int
    y: int
    w: int
    h: int

    def contains(self, px: int, py: int) -> bool:
        return self.x <= px < self.x + self.w and self.y <= py < self.y + self.h

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2


@dataclass
class FormScreen:
    """A sign-up form. With `layout_shift`, a cookie banner pushes everything
    down by 60 px right after the first screenshot (a classic real-world trap)."""

    layout_shift: bool = False
    elements: list[Element] = field(
        default_factory=lambda: [
            Element("name_field", 100, 100, 300, 30),
            Element("email_field", 100, 150, 300, 30),
            Element("submit_button", 100, 200, 120, 40),
        ]
    )
    values: dict[str, str] = field(default_factory=dict)
    focused: str | None = None
    submitted: bool = False
    screenshots: int = 0
    log: list[str] = field(default_factory=list)

    def screenshot(self) -> str:
        self.screenshots += 1
        view = "; ".join(
            f"{e.name} at ({e.x},{e.y},{e.w}x{e.h}) value={self.values.get(e.name, '')!r}"
            for e in self.elements
        )
        if self.layout_shift and self.screenshots == 1:
            for e in self.elements:
                e.y += 60  # the banner appears *after* the model has seen the screen
        return f"submitted={self.submitted}; {view}"

    def apply(self, a: Action) -> str:
        if a.kind == "screenshot":
            return self.screenshot()
        if a.kind == "click":
            hit = next((e for e in self.elements if e.contains(a.x, a.y)), None)
            self.log.append(f"click({a.x},{a.y}) -> {hit.name if hit else 'nothing'}")
            if hit is None:
                return "OK"  # like a real screen: a missed click raises no error
            if hit.name == "submit_button":
                self.submitted = True
            else:
                self.focused = hit.name
            return "OK"
        if a.kind == "type":
            if self.focused:
                self.values[self.focused] = self.values.get(self.focused, "") + a.text
            return "OK"
        if a.kind == "key":
            return "OK"
        return "done"


def task_succeeded(screen: FormScreen, name: str, email: str) -> bool:
    """State-based check: never trust the agent's own claim of success."""
    return (
        screen.submitted
        and screen.values.get("name_field") == name
        and screen.values.get("email_field") == email
    )


# ----------------------------------------------------------------------------- loop

Policy = Callable[[list[str]], list[Action]]  # observations so far -> next batch of actions


def run(screen: FormScreen, policy: Policy, max_steps: int = 10) -> tuple[bool, int]:
    """Returns (agent_claimed_done, steps). Batches run in order and stop at 'done'."""
    observations = [screen.screenshot()]
    for step in range(1, max_steps + 1):
        for action in policy(observations):
            if action.kind == "done":
                return True, step
            observations.append(screen.apply(action))
    return False, max_steps


def _find(obs: str, name: str) -> tuple[int, int]:
    part = obs.split(f"{name} at (", 1)[1]
    x, y, wh = part.split(",", 2)
    w, h = wh.split(")")[0].split("x")
    return int(x) + int(w) // 2, int(y) + int(h) // 2


def fill_actions(obs: str, name: str, email: str) -> list[Action]:
    nx, ny = _find(obs, "name_field")
    ex, ey = _find(obs, "email_field")
    sx, sy = _find(obs, "submit_button")
    return [
        Action("click", nx, ny),
        Action("type", text=name),
        Action("click", ex, ey),
        Action("type", text=email),
        Action("click", sx, sy),
    ]


def naive_policy(name: str, email: str) -> Policy:
    """Acts on the first screenshot only, then declares victory without checking."""

    def policy(observations: list[str]) -> list[Action]:
        if len(observations) == 1:
            return fill_actions(observations[0], name, email) + [Action("done")]
        return [Action("done")]

    return policy


def careful_policy(name: str, email: str) -> Policy:
    """Re-observes before acting and verifies the result before saying 'done'."""

    def policy(observations: list[str]) -> list[Action]:
        last = observations[-1]
        if last.startswith("submitted=True") and f"value={email!r}" in last:
            return [Action("done")]
        if len(observations) == 1 or not last.startswith("submitted="):
            return [Action("screenshot")]  # fresh view before acting
        return fill_actions(last, name, email) + [Action("screenshot")]

    return policy


if __name__ == "__main__":
    for label, make in (("naive", naive_policy), ("careful", careful_policy)):
        screen = FormScreen(layout_shift=True)
        claimed, steps = run(screen, make("Ada", "ada@example.com"))
        ok = task_succeeded(screen, "Ada", "ada@example.com")
        print(f"{label:8s} claimed_done={claimed} actually_succeeded={ok} steps={steps}")
        print("   ", screen.log)
