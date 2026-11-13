"""L5.1: plan-then-execute, with replanning when an observation breaks the plan.

The planner is a model that returns a JSON list of steps. The executor runs each
step with plain code (no model call per step: cheaper and more predictable than
ReAct for well-understood work). When a step fails, the planner is called again
with the failure, which is the "replan on new observations" part.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from aincourse import AssistantTurn, ChatModel, Message, ScriptedModel


@dataclass(frozen=True)
class Step:
    tool: str
    args: dict


@dataclass
class PlanRun:
    done: bool
    executed: list[str] = field(default_factory=list)
    plans: int = 0
    reason: str = ""


def parse_plan(text: str) -> list[Step]:
    return [Step(s["tool"], s.get("args", {})) for s in json.loads(text)]


def plan_and_execute(
    planner: ChatModel,
    tools: dict[str, Callable[..., str]],
    goal: str,
    max_replans: int = 2,
) -> PlanRun:
    run = PlanRun(done=False)
    messages = [
        Message("system", "Return a JSON list of {tool, args} steps."),
        Message("user", goal),
    ]
    while run.plans <= max_replans:
        plan = parse_plan(planner.complete(messages).text)
        run.plans += 1
        failure = None
        for step in plan:
            try:
                out = tools[step.tool](**step.args)
            except Exception as err:  # the observation that triggers replanning
                failure = f"step {step.tool}({step.args}) failed: {err}"
                break
            run.executed.append(f"{step.tool} -> {out}")
        if failure is None:
            run.done = True
            return run
        messages.append(
            Message("user", f"{failure}. Executed so far: {run.executed}. Replan the rest.")
        )
    run.reason = "replan budget exhausted"
    return run


def demo() -> PlanRun:
    """Transcode a clip; the first plan assumes a codec the device lacks."""

    def probe(path: str) -> str:
        return "h264 1080p"

    def transcode(path: str, codec: str) -> str:
        if codec == "av1":
            raise RuntimeError("encoder av1 not available on this build")
        return f"{path}.{codec}.mp4"

    def upload(path: str) -> str:
        return f"uploaded {path}"

    planner = ScriptedModel(
        [
            AssistantTurn(
                text=json.dumps(
                    [
                        {"tool": "probe", "args": {"path": "clip.mov"}},
                        {"tool": "transcode", "args": {"path": "clip.mov", "codec": "av1"}},
                        {"tool": "upload", "args": {"path": "clip.mov.av1.mp4"}},
                    ]
                )
            ),
            AssistantTurn(
                text=json.dumps(
                    [
                        {"tool": "transcode", "args": {"path": "clip.mov", "codec": "hevc"}},
                        {"tool": "upload", "args": {"path": "clip.mov.hevc.mp4"}},
                    ]
                )
            ),
        ]
    )
    return plan_and_execute(
        planner, {"probe": probe, "transcode": transcode, "upload": upload}, "Publish clip.mov"
    )


if __name__ == "__main__":
    r = demo()
    print(f"done={r.done} plans={r.plans}")
    for line in r.executed:
        print("  ", line)
