"""L4.5: progressive disclosure. Load skills and docs only when needed.

The prompt carries a one-line index of every skill (name + description). The
full body is loaded by a `load_skill` tool when the model decides it needs it.
Same idea as Agent Skills / SKILL.md files, covered properly in M10.
"""

from __future__ import annotations

from dataclasses import dataclass

from context_budget import approx_tokens


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str


SKILLS = [
    Skill(
        "ffmpeg-recipes",
        "Trim, transcode and normalise audio/video with ffmpeg.",
        "ffmpeg -ss 5 -t 10 -i in.mp4 -c copy out.mp4\n" * 80,
    ),
    Skill(
        "adb-basics",
        "Drive an Android device or emulator with adb.",
        "adb exec-out screencap -p > s.png\n" * 80,
    ),
    Skill(
        "release-notes",
        "Write release notes from merged PRs.",
        "Group by feature, fix, chore...\n" * 80,
    ),
]


def index_prompt(skills: list[Skill]) -> str:
    return "Skills (call load_skill(name) to read one):\n" + "\n".join(
        f"- {s.name}: {s.description}" for s in skills
    )


def load_skill(name: str, skills: list[Skill] = SKILLS) -> str:
    for s in skills:
        if s.name == name:
            return s.body
    return f"error: no skill {name!r}; available: {[s.name for s in skills]}"


def savings(
    skills: list[Skill] = SKILLS, loaded: tuple[str, ...] = ("ffmpeg-recipes",)
) -> tuple[int, int]:
    """(tokens if everything is inlined, tokens with index + loaded bodies)."""
    everything = sum(approx_tokens(s.body) for s in skills)
    disclosed = approx_tokens(index_prompt(skills)) + sum(
        approx_tokens(load_skill(n, skills)) for n in loaded
    )
    return everything, disclosed


if __name__ == "__main__":
    print("inline everything vs progressive disclosure:", savings())
