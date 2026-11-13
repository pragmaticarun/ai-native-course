"""L6.1/L6.3: graders. Evals are the unit tests of agents.

* exact: the answer must equal the reference (after normalising whitespace/case);
* programmatic: any Python check (contains, regex, parses as JSON, runs the tests...);
* LLM-as-judge: a model scores against a rubric; calibrate it against humans (M6 Ex1);
* trajectory: grade the sequence of tool calls, not just the final answer.

A `Case` pairs an input with graders; `run_suite` gives a pass rate and the failures,
which is what a regression suite checks in CI.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from aincourse import ChatModel, Message

Grader = Callable[[str, list[str]], str | None]  # (answer, tool trajectory) -> failure or None


def exact(expected: str) -> Grader:
    def g(answer: str, traj: list[str]) -> str | None:
        norm = lambda s: " ".join(s.lower().split())  # noqa: E731
        return None if norm(answer) == norm(expected) else f"expected {expected!r}"

    return g


def contains(*needles: str) -> Grader:
    def g(answer: str, traj: list[str]) -> str | None:
        missing = [n for n in needles if n.lower() not in answer.lower()]
        return f"missing {missing}" if missing else None

    return g


def matches(pattern: str) -> Grader:
    def g(answer: str, traj: list[str]) -> str | None:
        return None if re.search(pattern, answer) else f"no match for /{pattern}/"

    return g


def judge(model: ChatModel, rubric: str, threshold: int = 4) -> Grader:
    """The judge replies with a 1-5 score on the first line. Calibrate before trusting it."""

    def g(answer: str, traj: list[str]) -> str | None:
        reply = model.complete([Message("system", rubric), Message("user", answer)]).text
        m = re.match(r"\s*([1-5])", reply)
        if not m:
            return f"judge reply unparseable: {reply!r}"
        return None if int(m.group(1)) >= threshold else f"judge score {m.group(1)} < {threshold}"

    return g


# ------------------------------------------------------------------ trajectory graders


def calls_first(tool: str) -> Grader:
    def g(answer: str, traj: list[str]) -> str | None:
        return None if traj and traj[0] == tool else f"first call should be {tool}, got {traj[:1]}"

    return g


def at_most_calls(n: int) -> Grader:
    def g(answer: str, traj: list[str]) -> str | None:
        return None if len(traj) <= n else f"{len(traj)} tool calls > {n}"

    return g


def never_calls(*tools: str) -> Grader:
    def g(answer: str, traj: list[str]) -> str | None:
        bad = [t for t in traj if t in tools]
        return f"forbidden calls {bad}" if bad else None

    return g


def in_order(*tools: str) -> Grader:
    """`tools` must appear as a subsequence of the trajectory."""

    def g(answer: str, traj: list[str]) -> str | None:
        it = iter(traj)
        return None if all(t in it for t in tools) else f"expected order {list(tools)} in {traj}"

    return g


@dataclass
class Case:
    id: str
    input: str
    graders: Sequence[Grader]
    tags: tuple[str, ...] = ()


@dataclass
class SuiteResult:
    passed: int
    total: int
    failures: dict[str, list[str]] = field(default_factory=dict)

    @property
    def rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


def run_suite(cases: Sequence[Case], agent: Callable[[str], tuple[str, list[str]]]) -> SuiteResult:
    res = SuiteResult(0, len(cases))
    for case in cases:
        answer, traj = agent(case.input)
        problems = [p for g in case.graders if (p := g(answer, traj))]
        if problems:
            res.failures[case.id] = problems
        else:
            res.passed += 1
    return res
