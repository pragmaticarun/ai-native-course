"""M10 L10.1-L10.2: read Spec Kit and Kiro spec files, lint them, and turn them into tests.

The section names, `**Given** / **When** / **Then**` scenarios, `FR-###` / `SC-###` ids,
`[NEEDS CLARIFICATION: ...]` markers and the `T### [P] [US#]` task format all come from
the templates that `specify init` (Spec Kit v1.4.0) writes into `.specify/templates/`.
Kiro's `WHEN ... THE SYSTEM SHALL ...` lines are EARS notation, as its docs describe.

Two things here are this course's own conventions, not Spec Kit's or Kiro's:
* the lint rules (vague words, a stated out-of-scope list), and
* the oracle convention: a scenario whose Given and Then each carry one backticked
  value is an executable example (`error` means "must be rejected").
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from graphlib import TopologicalSorter

PLACEHOLDER = re.compile(r"\[(?!NEEDS CLARIFICATION)[A-Z#][^\]\n]*\]")
CLARIFY = re.compile(r"\[NEEDS CLARIFICATION:\s*([^\]]+)\]")
STORY = re.compile(r"^### User Story (\d+) - (.+?) \(Priority: (P\d+)\)", re.M)
SCENARIO = re.compile(
    r"^\d+\.\s+\*\*Given\*\*(.+?),\s*\*\*When\*\*(.+?),\s*\*\*Then\*\*(.+)$", re.M
)
REQ = re.compile(r"^- \*\*((?:FR|SC)-\d{3})\*\*:\s*(.+)$", re.M)
TASK = re.compile(r"^- \[( |x|X)\] (T\d{3})((?: \[P\])?)((?: \[US\d+\])?) (.+)$", re.M)
DEPENDS = re.compile(r"\(depends on ([T\d, ]+)\)")
EARS = re.compile(r"WHEN (.+?) THE SYSTEM SHALL (.+)$", re.M)
TICKS = re.compile(r"`([^`]*)`")
# Course lint: words that make a requirement untestable unless a number follows.
VAGUE = ("fast", "quickly", "user-friendly", "intuitive", "robust", "scalable", "easy", "secure")


@dataclass
class Scenario:
    given: str
    when: str
    then: str


@dataclass
class Story:
    number: int
    title: str
    priority: str
    scenarios: list[Scenario] = field(default_factory=list)


@dataclass
class Spec:
    title: str
    stories: list[Story]
    requirements: dict[str, str]
    criteria: dict[str, str]
    clarifications: list[str]
    placeholders: list[str]
    sections: list[str]
    assumptions: list[str]


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}.*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def parse_spec(text: str) -> Spec:
    body = re.sub(r"<!--.*?-->", "", text, flags=re.S)  # template comments aren't content
    title_m = re.search(r"^# Feature Specification: (.+)$", body, re.M)
    stories: list[Story] = []
    starts = list(STORY.finditer(body))
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(body)
        chunk = body[m.end() : end].split("\n### ", 1)[0]
        scen = [Scenario(*(s.strip() for s in g.groups())) for g in SCENARIO.finditer(chunk)]
        stories.append(Story(int(m.group(1)), m.group(2), m.group(3), scen))
    reqs = dict(REQ.findall(body))
    assumptions = [
        ln[2:].strip() for ln in _section(body, "Assumptions").splitlines() if ln.startswith("- ")
    ]
    return Spec(
        title=title_m.group(1).strip() if title_m else "",
        stories=stories,
        requirements={k: v for k, v in reqs.items() if k.startswith("FR")},
        criteria={k: v for k, v in reqs.items() if k.startswith("SC")},
        clarifications=CLARIFY.findall(body),
        placeholders=sorted(set(PLACEHOLDER.findall(body))),
        sections=re.findall(r"^## (.+?)(?: \*\(mandatory\)\*)?$", body, re.M),
        assumptions=assumptions,
    )


def lint_spec(spec: Spec) -> list[str]:
    problems: list[str] = []
    for needed in ("User Scenarios & Testing", "Requirements", "Success Criteria"):
        if needed not in spec.sections:
            problems.append(f"missing section: {needed}")
    problems += [f"template placeholder left: {p}" for p in spec.placeholders]
    problems += [f"unresolved: {c.strip()}" for c in spec.clarifications]
    if not spec.stories:
        problems.append("no user stories")
    for s in spec.stories:
        if not s.scenarios:
            problems.append(f"US{s.number} has no acceptance scenarios")
    if not spec.requirements:
        problems.append("no functional requirements")
    for rid, text in {**spec.requirements, **spec.criteria}.items():
        for word in VAGUE:
            if re.search(rf"\b{word}\b", text, re.I) and not re.search(r"\d", text):
                problems.append(f"{rid}: '{word}' without a number is not testable")
    if not spec.criteria:
        problems.append("no measurable success criteria")
    if not any(a.lower().startswith(("out of scope", "non-goal")) for a in spec.assumptions):
        problems.append("no out-of-scope / non-goals line in Assumptions")
    return problems


@dataclass
class Task:
    id: str
    done: bool
    parallel: bool
    story: str | None
    text: str
    depends: list[str]
    paths: list[str]


def parse_tasks(text: str) -> list[Task]:
    tasks = []
    for done, tid, par, story, rest in TASK.findall(text):
        dep = DEPENDS.search(rest)
        tasks.append(
            Task(
                id=tid,
                done=done.lower() == "x",
                parallel=bool(par),
                story=story.strip(" []") or None,
                text=rest,
                depends=[d.strip() for d in dep.group(1).split(",")] if dep else [],
                paths=re.findall(r"\b(?:src|tests|app|lib)/[\w/.-]+\.\w+", rest),
            )
        )
    return tasks


def lint_tasks(tasks: list[Task], spec: Spec) -> list[str]:
    problems: list[str] = []
    ids = [t.id for t in tasks]
    if len(ids) != len(set(ids)):
        problems.append("duplicate task ids")
    known = set(ids)
    stories = {f"US{s.number}" for s in spec.stories}
    for t in tasks:
        if t.story and t.story not in stories:
            problems.append(f"{t.id}: unknown story {t.story}")
        problems += [f"{t.id}: depends on unknown {d}" for d in t.depends if d not in known]
    for s in sorted(stories - {t.story for t in tasks}):
        problems.append(f"{s} has no tasks")
    # [P] means "different files, no dependencies": two [P] tasks on one file contradict it.
    seen: dict[str, str] = {}
    for t in tasks:
        if t.parallel:
            for p in t.paths:
                if p in seen:
                    problems.append(f"{t.id} and {seen[p]} are both [P] but touch {p}")
                seen.setdefault(p, t.id)
    return problems


def waves(tasks: list[Task]) -> list[list[str]]:
    """Group tasks into waves: each wave only depends on earlier waves (what Kiro's docs
    describe for running a spec's tasks in parallel)."""
    ts = TopologicalSorter({t.id: set(t.depends) for t in tasks})
    ts.prepare()
    out: list[list[str]] = []
    while ts.is_active():
        ready = sorted(ts.get_ready())
        out.append(ready)
        ts.done(*ready)
    return out


@dataclass
class Example:
    source: str
    given: str
    expected: str


def examples_from_spec(spec: Spec) -> list[Example]:
    out = []
    for s in spec.stories:
        for i, sc in enumerate(s.scenarios, 1):
            g, t = TICKS.findall(sc.given), TICKS.findall(sc.then)
            if len(g) == 1 and len(t) == 1:
                out.append(Example(f"US{s.number}.{i}", g[0], t[0]))
    return out


def examples_from_ears(text: str) -> list[Example]:
    out = []
    for i, (cond, shall) in enumerate(EARS.findall(text), 1):
        g, t = TICKS.findall(cond), TICKS.findall(shall)
        if len(g) == 1 and len(t) == 1:
            out.append(Example(f"EARS.{i}", g[0], t[0]))
    return out


def check(examples: list[Example], fn: Callable[[str], object]) -> list[str]:
    """Run each example against an implementation; return the ids that fail."""
    failed = []
    for ex in examples:
        try:
            got: object = fn(ex.given)
            ok = ex.expected != "error" and str(got) == ex.expected
        except ValueError:
            ok = ex.expected == "error"
        if not ok:
            failed.append(ex.source)
    return failed
