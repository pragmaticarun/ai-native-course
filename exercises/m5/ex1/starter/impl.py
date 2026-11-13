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
    # TODO: detect failures (exceptions AND unexpected output) and replan.
    result = Result(done=True)
    for step in plan:
        try:
            result.executed.append(tools[step.tool](**step.args))
        except Exception:
            pass
    return result
