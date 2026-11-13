"""M10 L10.3: which instructions does an agent see for a given file?

* AGENTS.md (agents.md): plain Markdown; nested files are allowed and "the closest
  AGENTS.md to the edited file wins". `agents_chain` returns root → closest, so the
  most specific text comes last.
* Cursor project rules (cursor.com/docs/rules): `.cursor/rules/**/*.mdc` with
  `description`, `globs` (comma-separated) and `alwaysApply` frontmatter. The four
  behaviours below are the table in Cursor's docs.
* Claude Code path rules (code.claude.com/docs/en/memory): `.claude/rules/**/*.md`;
  `paths` is the only frontmatter field it reads.

`lint_instructions` is this course's checklist, not part of any of those formats.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """`**` = any number of directories, `*` = within one path segment, `{a,b}` = either."""
    out, i = "", 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif c == "*":
            out, i = out + "[^/]*", i + 1
        elif c == "?":
            out, i = out + "[^/]", i + 1
        elif c == "{":
            end = pattern.index("}", i)
            out += "(?:" + "|".join(map(re.escape, pattern[i + 1 : end].split(","))) + ")"
            i = end + 1
        else:
            out, i = out + re.escape(c), i + 1
    return re.compile(f"^{out}$")


def glob_match(pattern: str, path: str) -> bool:
    return bool(glob_to_regex(pattern.strip().lstrip("/")).match(path))


def agents_chain(repo: Path, file: str) -> list[Path]:
    """AGENTS.md files that apply to `file` (relative to repo), root first."""
    chain = []
    d = (repo / file).parent
    while True:
        if (d / "AGENTS.md").is_file():
            chain.append(d / "AGENTS.md")
        if d == repo:
            break
        d = d.parent
    return list(reversed(chain))


def split_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---\n"):
        end = text.index("\n---", 4)
        return yaml.safe_load(text[4:end]) or {}, text[end + 4 :].lstrip("\n")
    return {}, text


@dataclass
class Rule:
    name: str
    description: str | None
    globs: list[str]
    always: bool
    body: str

    @property
    def mode(self) -> str:
        if self.always:
            return "always"
        if self.globs:
            return "auto-attached"
        if self.description:
            return "agent-requested"
        return "manual"


def load_cursor_rules(repo: Path) -> list[Rule]:
    rules = []
    for f in sorted((repo / ".cursor" / "rules").rglob("*")):
        if f.suffix != ".mdc":  # a plain .md here is ignored by Cursor
            continue
        meta, body = split_frontmatter(f.read_text())
        globs = meta.get("globs") or []
        if isinstance(globs, str):
            globs = [g.strip() for g in globs.split(",") if g.strip()]
        rules.append(
            Rule(f.stem, meta.get("description"), globs, bool(meta.get("alwaysApply")), body)
        )
    return rules


def cursor_context(rules: list[Rule], files: list[str]) -> dict[str, list[str]]:
    """What goes into context up front, and what the agent may pull in itself."""
    attached = [
        r.name
        for r in rules
        if r.mode == "always"
        or (r.mode == "auto-attached" and any(glob_match(g, f) for g in r.globs for f in files))
    ]
    offered = [r.name for r in rules if r.mode == "agent-requested"]
    return {"included": attached, "offered_by_description": offered}


def claude_rules_for(repo: Path, file: str) -> list[str]:
    out = []
    for f in sorted((repo / ".claude" / "rules").rglob("*.md")):
        meta, _ = split_frontmatter(f.read_text())
        paths = meta.get("paths")
        if isinstance(paths, str):
            paths = [p.strip() for p in paths.split(",")]
        if not paths or any(glob_match(p, file) for p in paths):
            out.append(f.stem)
    return out


SECRET = re.compile(
    r"(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)
VAGUE_RULES = re.compile(
    r"\b(write (good|clean) code|be careful|use best practices|as needed)\b", re.I
)


def lint_instructions(text: str, repo: Path, max_lines: int = 200) -> list[str]:
    """Course checklist for AGENTS.md / CLAUDE.md. 200 lines follows Claude Code's
    guidance for CLAUDE.md ("target under 200 lines per CLAUDE.md file")."""
    problems = []
    if len(text.splitlines()) > max_lines:
        problems.append(f"longer than {max_lines} lines: move detail into skills or path rules")
    if SECRET.search(text):
        problems.append("contains something that looks like a credential")
    problems += [f"vague instruction: '{m.group(0)}'" for m in VAGUE_RULES.finditer(text)]
    targets = _make_targets(repo)
    for target in re.findall(r"`make ([\w-]+)`", text):
        if target not in targets:
            problems.append(f"documents `make {target}` but the Makefile has no such target")
    for script in re.findall(r"`pnpm (?:run )?([\w:-]+)`", text):
        if script not in _pnpm_scripts(repo) and script not in {"install", "vitest", "exec", "dlx"}:
            problems.append(f"documents `pnpm {script}` but package.json has no such script")
    return problems


def _make_targets(repo: Path) -> set[str]:
    mk = repo / "Makefile"
    return set(re.findall(r"^([\w-]+):", mk.read_text(), re.M)) if mk.exists() else set()


def _pnpm_scripts(repo: Path) -> set[str]:
    import json

    pj = repo / "package.json"
    return set(json.loads(pj.read_text()).get("scripts", {})) if pj.exists() else set()
