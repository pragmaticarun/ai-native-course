from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Step:
    tool: str
    args: dict
    expect: str


@dataclass
class Result:
    done: bool
    executed: list[str] = field(default_factory=list)
    replans: int = 0


def execute(
    plan: list[Step],
    tools: dict[str, Callable[..., str]],
    replan: Callable[[list[str], str], list[Step]],
    max_replans: int = 2,
) -> Result:
    result = Result(done=False)
    queue = list(plan)
    while queue:
        step = queue.pop(0)
        try:
            out = tools[step.tool](**step.args)
            failure = (
                None
                if step.expect in out
                else f"{step.tool}: expected {step.expect!r}, got {out!r}"
            )
        except Exception as err:
            failure = f"{step.tool}: {err}"
        if failure is None:
            result.executed.append(out)
            continue
        if result.replans >= max_replans:
            return result
        result.replans += 1
        queue = replan(list(result.executed), failure)
    result.done = True
    return result
