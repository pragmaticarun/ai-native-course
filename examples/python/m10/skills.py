"""M10 L10.4: Agent Skills — validate SKILL.md and show progressive disclosure.

Rules from the Agent Skills specification (agentskills.io/specification):
* `name`: 1-64 chars, lowercase a-z, 0-9 and hyphens, no leading/trailing or double
  hyphen, and it must match the directory name.
* `description`: 1-1024 chars, says what the skill does and when to use it.
* optional `license`, `compatibility` (≤500 chars), `metadata` (string → string),
  `allowed-tools` (experimental).
* progressive disclosure: name + description at startup, the body on activation,
  files under scripts/ references/ assets/ only when needed. Keep SKILL.md under
  500 lines; keep file references one level deep.

Fields outside the spec (e.g. Spec Kit's generated skills carry `user-invocable`,
`argument-hint`) are reported as warnings: some agents read them, the spec doesn't.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from rules import split_frontmatter

NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
REF = re.compile(r"(?<![\w/])((?:scripts|references|assets)/[\w./-]+)")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_skill(skill_dir: Path) -> Report:
    r = Report()
    f = skill_dir / "SKILL.md"
    if not f.is_file():
        r.errors.append("no SKILL.md")
        return r
    text = f.read_text()
    if not text.startswith("---\n"):
        r.errors.append("SKILL.md must start with YAML frontmatter")
        return r
    meta, body = split_frontmatter(text)
    name, desc = meta.get("name"), meta.get("description")
    if not isinstance(name, str) or not 1 <= len(name) <= 64 or not NAME.match(name):
        r.errors.append(f"invalid name {name!r}: lowercase letters, digits, single hyphens, ≤64")
    elif name != skill_dir.name:
        r.errors.append(f"name {name!r} must match directory {skill_dir.name!r}")
    if not isinstance(desc, str) or not 1 <= len(desc) <= 1024:
        r.errors.append("description must be 1-1024 characters")
    elif not re.search(r"\b(use (it |this )?(when|for|to)|when)\b", desc, re.I):
        r.warnings.append("description doesn't say when to use the skill")
    comp = meta.get("compatibility")
    if comp is not None and (not isinstance(comp, str) or not 1 <= len(comp) <= 500):
        r.errors.append("compatibility must be 1-500 characters")
    md = meta.get("metadata")
    if md is not None and not (
        isinstance(md, dict) and all(isinstance(v, str) for v in md.values())
    ):
        r.errors.append("metadata must map strings to strings")
    r.warnings += [
        f"field not in the Agent Skills spec: {k}" for k in sorted(set(meta) - SPEC_FIELDS)
    ]
    if len(body.splitlines()) > 500:
        r.warnings.append("body over 500 lines: move detail into references/")
    for ref in sorted(set(REF.findall(body))):
        ref = ref.rstrip(".")
        if not (skill_dir / ref).exists():
            r.errors.append(f"references missing file {ref}")
        elif ref.count("/") > 1:
            r.warnings.append(f"{ref}: keep references one level deep")
    return r


@dataclass
class SkillCatalog:
    """What an agent host does with a skills directory. `loaded` counts characters put
    into the model's context, to show what progressive disclosure saves."""

    root: Path
    loaded: int = 0
    log: list[str] = field(default_factory=list)

    def entries(self) -> dict[str, str]:
        out = {}
        for d in sorted(p for p in self.root.iterdir() if (p / "SKILL.md").is_file()):
            meta, _ = split_frontmatter((d / "SKILL.md").read_text())
            out[str(meta["name"])] = str(meta["description"])
        return out

    def startup_prompt(self) -> str:
        text = "\n".join(f"- {n}: {d}" for n, d in self.entries().items())
        self._load("catalog", text)
        return text

    def choose(self, task: str) -> str | None:
        """Stand-in for the model's choice: most words shared with the description."""
        words = set(re.findall(r"[a-z]+", task.lower()))
        scored = [
            (len(words & set(re.findall(r"[a-z]+", d.lower()))), n)
            for n, d in self.entries().items()
        ]
        best = max(scored, default=(0, ""))
        return best[1] if best[0] >= 2 else None

    def activate(self, name: str) -> str:
        _, body = split_frontmatter((self.root / name / "SKILL.md").read_text())
        self._load(f"activate {name}", body)
        return body

    def resource(self, name: str, rel: str) -> str:
        text = (self.root / name / rel).read_text()
        self._load(f"read {name}/{rel}", text)
        return text

    def _load(self, what: str, text: str) -> None:
        self.loaded += len(text)
        self.log.append(f"{what}: {len(text)} chars")
