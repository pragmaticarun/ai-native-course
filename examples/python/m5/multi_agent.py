"""L5.3: multi-agent patterns, and the case against them.

* agent-as-tool: the main agent calls a specialist like a function;
* supervisor/worker: a supervisor routes subtasks to workers and merges results;
* handoff: control moves to another agent, which owns the conversation from then on.

Every "agent" here is a ScriptedModel plus a role prompt, so the tests can count
model calls. The single-agent version does the same job with fewer calls; that
is usually the right default (fewer hops, less lost context, cheaper evals).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from aincourse import AssistantTurn, ChatModel, Message, ScriptedModel


@dataclass
class Agent:
    name: str
    role: str
    model: ChatModel
    calls: int = 0

    def run(self, task: str) -> str:
        self.calls += 1
        return self.model.complete([Message("system", self.role), Message("user", task)]).text


@dataclass
class Ledger:
    hops: list[str] = field(default_factory=list)


def as_tool(agent: Agent, ledger: Ledger) -> Callable[[str], str]:
    def call(task: str) -> str:
        ledger.hops.append(f"tool:{agent.name}")
        return agent.run(task)

    return call


def supervisor(
    route: Callable[[str], list[tuple[str, str]]],
    workers: dict[str, Agent],
    task: str,
    ledger: Ledger,
) -> str:
    """`route` is the supervisor's decision (a model in real life) of (worker, subtask) pairs."""
    parts = []
    for worker, sub in route(task):
        ledger.hops.append(f"worker:{worker}")
        parts.append(workers[worker].run(sub))
    return "\n".join(parts)


def handoff(triage: Agent, specialists: dict[str, Agent], task: str, ledger: Ledger) -> str:
    target = triage.run(task).strip()
    ledger.hops.append(f"handoff:{target}")
    if target not in specialists:
        return f"error: triage picked unknown agent {target!r}"
    return specialists[target].run(task)  # the specialist now owns the conversation


def echo(prefix: str) -> ScriptedModel:
    return ScriptedModel(lambda msgs, tools: AssistantTurn(text=f"{prefix}: {msgs[-1].content}"))


def three_agent_release(commits: list[str]) -> tuple[str, int]:
    ledger = Ledger()
    workers = {
        "features": Agent("features", "Summarise features.", echo("Features")),
        "fixes": Agent("fixes", "Summarise fixes.", echo("Fixes")),
    }

    def route(task: str) -> list[tuple[str, str]]:
        feats = [c for c in commits if c.startswith("feat")]
        fixes = [c for c in commits if c.startswith("fix")]
        return [("features", "; ".join(feats)), ("fixes", "; ".join(fixes))]

    supervisor_agent = Agent("supervisor", "Route work.", echo("Plan"))
    supervisor_agent.run("plan the release notes")  # the routing call
    out = supervisor(route, workers, "release notes", ledger)
    calls = supervisor_agent.calls + sum(w.calls for w in workers.values())
    return out, calls


def single_agent_release(commits: list[str]) -> tuple[str, int]:
    feats = "; ".join(c for c in commits if c.startswith("feat"))
    fixes = "; ".join(c for c in commits if c.startswith("fix"))

    def write(msgs, tools):  # one call writes both sections
        return AssistantTurn(text=f"Features: {feats}\nFixes: {fixes}")

    agent = Agent(
        "writer", "Write release notes with Features and Fixes sections.", ScriptedModel(write)
    )
    return agent.run("\n".join(commits)), agent.calls


if __name__ == "__main__":
    commits = ["feat: add AV1 decode", "fix: crash on empty playlist", "feat: HDR tone mapping"]
    print(three_agent_release(commits))
    print(single_agent_release(commits))
