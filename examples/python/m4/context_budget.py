"""L4.1: context as a scarce resource.

Build the prompt from prioritised sections under a token budget:

    1. instructions (never dropped)
    2. tool specs   (never dropped)
    3. retrieved data (truncated first, most relevant kept)
    4. history      (oldest turns dropped first, newest kept)

Token counts use a deliberately rough estimate (4 characters per token). Real
tokenizers differ by model; use the provider's own counter when it matters.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def approx_tokens(text: str) -> int:
    return (len(text) + 3) // 4


def truncate_to_tokens(text: str, max_tokens: int, marker: str = " …[truncated]") -> str:
    """Cut a tool result or document so it fits, and say so (the model should know)."""
    if approx_tokens(text) <= max_tokens:
        return text
    keep = max(0, max_tokens * 4 - len(marker))
    return text[:keep] + marker


@dataclass
class ContextReport:
    prompt: str
    tokens: int
    dropped_history: int = 0
    truncated_docs: int = 0
    sections: dict[str, int] = field(default_factory=dict)


def build_context(
    instructions: str,
    tool_specs: str,
    retrieved: list[str],
    history: list[str],
    budget: int,
    per_doc_cap: int = 400,
) -> ContextReport:
    """Assemble the prompt; raise if the fixed part alone exceeds the budget."""
    fixed = [instructions, tool_specs]
    used = sum(approx_tokens(s) for s in fixed)
    if used > budget:
        raise ValueError(f"instructions + tools need {used} tokens; budget is {budget}")

    docs: list[str] = []
    truncated = 0
    for doc in retrieved:  # most relevant first
        capped = truncate_to_tokens(doc, per_doc_cap)
        truncated += capped != doc
        cost = approx_tokens(capped)
        if used + cost > budget * 0.6:  # keep room for history
            truncated += 1
            continue
        docs.append(capped)
        used += cost

    kept: list[str] = []
    for turn in reversed(history):  # newest first
        cost = approx_tokens(turn)
        if used + cost > budget:
            break
        kept.append(turn)
        used += cost
    kept.reverse()

    parts = fixed + [f"<doc>{d}</doc>" for d in docs] + kept
    prompt = "\n\n".join(parts)
    return ContextReport(
        prompt=prompt,
        tokens=approx_tokens(prompt),
        dropped_history=len(history) - len(kept),
        truncated_docs=truncated,
        sections={
            "instructions": approx_tokens(instructions),
            "tools": approx_tokens(tool_specs),
            "retrieved": sum(approx_tokens(d) for d in docs),
            "history": sum(approx_tokens(t) for t in kept),
        },
    )


if __name__ == "__main__":
    history = [f"user: question {i}\nassistant: answer {i} " + "detail " * 40 for i in range(30)]
    report = build_context(
        "You answer questions about the repo. Cite file:line.",
        "tools: grep(pattern), read_range(path, start, end)",
        ["src/app.py:1-40 " + "code " * 600, "README.md:1-10 setup notes"],
        history,
        budget=2000,
    )
    print(report.sections, "dropped turns:", report.dropped_history, "total:", report.tokens)
