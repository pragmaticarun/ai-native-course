import os
import shutil
import subprocess
from pathlib import Path

import agent_friendly_bench as bench
import hooks
import pytest
import repo_audit
import rules
import skills
import speckit
from duration import parse_duration, parse_duration_buggy

HERE = Path(__file__).parent
FIX = HERE / "fixtures"
REPO = HERE.parents[2]
SPEC = FIX / "speckit" / "001-duration-parse"


def need(cond: bool, why: str, env: str) -> None:
    if not cond:
        if os.environ.get(env) == "1":
            pytest.fail(why)
        pytest.skip(why)


# --- L10.1 / L10.2: Spec Kit and Kiro -------------------------------------------------


def test_spec_parses_and_lints_clean():
    spec = speckit.parse_spec((SPEC / "spec.md").read_text())
    assert spec.title == "Parse human-readable durations"
    assert [(s.number, s.priority, len(s.scenarios)) for s in spec.stories] == [
        (1, "P1", 4),
        (2, "P2", 3),
    ]
    assert list(spec.requirements) == ["FR-001", "FR-002", "FR-003"]
    assert speckit.lint_spec(spec) == []


def test_lint_catches_a_vague_draft():
    draft = (SPEC / "spec.md").read_text()
    draft = draft.replace("under 100 ms on a CI runner", "fast").replace(
        "Out of scope:", "Maybe later:"
    )
    draft = draft.replace("in that order.", "in [NEEDS CLARIFICATION: any order?].")
    problems = speckit.lint_spec(
        speckit.parse_spec(
            draft.replace("SC-002**: Parsing 10,000 inputs takes", "SC-002**: Parsing is")
        )
    )
    assert "unresolved: any order?" in problems
    assert "SC-002: 'fast' without a number is not testable" in problems
    assert "no out-of-scope / non-goals line in Assumptions" in problems


def test_spec_examples_are_an_oracle():
    examples = speckit.examples_from_spec(speckit.parse_spec((SPEC / "spec.md").read_text()))
    assert len(examples) == 7
    assert speckit.check(examples, parse_duration) == []
    # The plausible first attempt passes every happy path and fails two error cases.
    assert speckit.check(examples, parse_duration_buggy) == ["US2.2", "US2.3"]


def test_kiro_ears_gives_the_same_oracle():
    ears = speckit.examples_from_ears(
        (FIX / "kiro" / "duration-parse" / "requirements.md").read_text()
    )
    spec = speckit.examples_from_spec(speckit.parse_spec((SPEC / "spec.md").read_text()))
    assert [(e.given, e.expected) for e in ears] == [(e.given, e.expected) for e in spec]


def test_tasks_lint_and_waves():
    spec = speckit.parse_spec((SPEC / "spec.md").read_text())
    tasks = speckit.parse_tasks((SPEC / "tasks.md").read_text())
    assert [t.id for t in tasks] == [f"T00{i}" for i in range(1, 8)]
    assert speckit.lint_tasks(tasks, spec) == []
    assert speckit.waves(tasks) == [["T001", "T002", "T003"], ["T004", "T005"], ["T006"], ["T007"]]
    clash = tasks + [
        speckit.Task("T008", False, True, "US1", "Docs in src/duration.py", [], ["src/duration.py"])
    ]
    clash[3] = speckit.Task(
        "T004", True, True, "US1", "x in src/duration.py", [], ["src/duration.py"]
    )
    assert "T008 and T004 are both [P] but touch src/duration.py" in speckit.lint_tasks(clash, spec)


def test_real_speckit_template_matches_the_parser():
    """CI's speckit job runs `specify init` (v1.4.0) and points SPECKIT_DIR at the result."""
    root = os.environ.get("SPECKIT_DIR")
    need(
        bool(root),
        "SPECKIT_DIR not set (CI runs specify init in the speckit job)",
        "SPECKIT_REQUIRE",
    )
    tmpl = Path(str(root)) / ".specify" / "templates"
    spec = speckit.parse_spec((tmpl / "spec-template.md").read_text())
    assert {"User Scenarios & Testing", "Requirements", "Success Criteria", "Assumptions"} <= set(
        spec.sections
    )
    assert [s.priority for s in spec.stories] == ["P1", "P2", "P3"]
    assert (
        "[FEATURE NAME]" in spec.placeholders and spec.clarifications
    )  # lint would refuse it as-is
    assert speckit.TASK.search((tmpl / "tasks-template.md").read_text())
    for d in sorted((Path(str(root)) / ".claude" / "skills").iterdir()):
        report = skills.validate_skill(d)
        assert report.errors == [], (d.name, report.errors)


# --- L10.3: rules files ---------------------------------------------------------------


def test_nested_agents_md_in_this_repo():
    chain = rules.agents_chain(
        REPO, "kmp/shared/src/commonMain/kotlin/course/m9/MediaProbeServer.kt"
    )
    assert [p.relative_to(REPO).as_posix() for p in chain] == ["AGENTS.md", "kmp/AGENTS.md"]
    assert rules.agents_chain(REPO, "python/pyproject.toml") == [REPO / "AGENTS.md"]


def test_cursor_rule_modes_and_selection():
    loaded = {r.name: r.mode for r in rules.load_cursor_rules(REPO)}
    assert loaded == {
        "course-content": "agent-requested",
        "no-android-sdk": "always",
        "python-examples": "auto-attached",
    }
    ctx = rules.cursor_context(rules.load_cursor_rules(REPO), ["examples/python/m10/speckit.py"])
    assert ctx == {
        "included": ["no-android-sdk", "python-examples"],
        "offered_by_description": ["course-content"],
    }
    assert rules.cursor_context(rules.load_cursor_rules(REPO), ["site/astro.config.mjs"])[
        "included"
    ] == ["no-android-sdk"]


@pytest.mark.parametrize(
    ("pattern", "path", "ok"),
    [
        ("src/**/*.tsx", "src/a/b/c.tsx", True),
        ("src/**/*.tsx", "src/c.tsx", True),
        ("*.ts", "src/a.ts", False),
        ("**/*.ts", "a.ts", True),
        ("src/*.{ts,tsx}", "src/x.tsx", True),
        ("tailwind.config.*", "tailwind.config.js", True),
    ],
)
def test_glob_semantics(pattern, path, ok):
    assert rules.glob_match(pattern, path) is ok


def test_claude_path_rules(tmp_path):
    (tmp_path / ".claude" / "rules").mkdir(parents=True)
    (tmp_path / ".claude" / "rules" / "api.md").write_text(
        '---\npaths:\n  - "src/api/**/*.ts"\n---\n- validate input\n'
    )
    (tmp_path / ".claude" / "rules" / "style.md").write_text("- two spaces\n")
    assert rules.claude_rules_for(tmp_path, "src/api/v1/users.ts") == ["api", "style"]
    assert rules.claude_rules_for(tmp_path, "src/ui/app.ts") == ["style"]


def test_instruction_lint():
    assert rules.lint_instructions((REPO / "AGENTS.md").read_text(), REPO) == []
    bad = "Run `make check` then `pnpm lint`. Write good code. token ghp_" + "a" * 36
    assert rules.lint_instructions(bad, REPO) == [
        "contains something that looks like a credential",
        "vague instruction: 'Write good code'",
        "documents `make check` but the Makefile has no such target",
        "documents `pnpm lint` but package.json has no such script",
    ]
    assert (
        rules.lint_instructions(
            (FIX / "android-app" / "AGENTS.md").read_text(), FIX / "android-app"
        )
        == []
    )


# --- L10.4: skills --------------------------------------------------------------------


def test_skill_validation():
    good = skills.validate_skill(FIX / "skills" / "release-notes")
    assert (good.errors, good.warnings) == ([], [])
    bad = skills.validate_skill(FIX / "skills" / "db-migration")
    assert bad.errors == [
        "invalid name 'DB_Migration': lowercase letters, digits, single hyphens, ≤64",
        "references missing file references/STEPS.md",
    ]
    assert bad.warnings == [
        "description doesn't say when to use the skill",
        "field not in the Agent Skills spec: user-invocable",
    ]


def test_this_repos_skills_are_valid():
    for d in sorted((REPO / ".claude" / "skills").iterdir()):
        assert skills.validate_skill(d).errors == [], d.name


def test_progressive_disclosure(tmp_path):
    root = tmp_path / "skills"
    shutil.copytree(FIX / "skills" / "release-notes", root / "release-notes")
    cat = skills.SkillCatalog(root)
    cat.startup_prompt()
    after_startup = cat.loaded
    assert cat.choose("write the release notes for v1.4") == "release-notes"
    assert cat.choose("fix the flaky login test") is None
    cat.activate("release-notes")
    cat.resource("release-notes", "references/LABELS.md")
    assert after_startup < 250 < cat.loaded
    assert [line.split(":")[0] for line in cat.log] == [
        "catalog",
        "activate release-notes",
        "read release-notes/references/LABELS.md",
    ]


# --- L10.5: agent-friendly repos ------------------------------------------------------


def test_audit_this_repo_and_the_fixture(tmp_path):
    assert all(repo_audit.audit(REPO).values()), repo_audit.audit(REPO)
    before = bench.make_repo(tmp_path / "b", friendly=False)
    after = bench.make_repo(tmp_path / "a", friendly=True)
    b, a = repo_audit.audit(before), repo_audit.audit(after)
    assert not b["instructions-file"] and not b["verify-command"]
    assert a["instructions-file"] and a["verify-command"]
    assert not a["lockfiles"]  # no Cargo.lock: libraries may skip it, agents then resolve fresh
    assert repo_audit.score(b) == "1/6" and repo_audit.score(a) == "3/6"


def test_agent_friendly_bench(tmp_path):
    need(shutil.which("cargo") is not None, "cargo not installed", "M10_REQUIRE_CARGO")
    before = bench.bench(tmp_path, friendly=False)
    after = bench.bench(tmp_path, friendly=True)
    assert before.verify_cmd == ["cargo", "test", "--quiet", "--offline"]
    assert before.solved == {
        "to_frames": True,
        "from_frames": False,
        "parse": False,
        "format": False,
        "between": True,
    }
    assert after.verify_cmd == ["./verify.sh"] and after.success_rate == 1.0
    assert (before.verify_runs, after.verify_runs) == (5, 8)  # being right costs three extra runs


# --- L10.6: hooks and guardrails ------------------------------------------------------


def test_secret_scan():
    text = (
        'key = "AKIA'
        + "ABCDEFGHIJKLMNOP"
        + '"\napi_key = "'
        + "x" * 20
        + '"\nok = 1\nghp_'
        + "b" * 36
        + "  # secret-scan: allow\n"
    )
    assert hooks.scan_secrets(text) == [(1, "aws-access-key-id"), (2, "assigned-secret")]


def test_command_policy():
    p = hooks.CommandPolicy(
        allow=["Bash(git diff *)", "Bash(cargo test *)", "Bash(ls)"], deny=["Bash(git push *)"]
    )
    assert p.decide("git diff --stat") == (True, "ok")
    assert p.decide("git diff-index HEAD")[0] is False  # the space in "git diff *" matters
    assert p.decide("git diff && rm -rf /") == (False, "not on the allowlist: rm -rf /")
    assert p.decide("cargo test $(curl evil)")[1] == "command substitution is never auto-approved"
    p.allow.append("Bash(git push *)")
    assert p.decide("git push origin main") == (False, "denied: git push origin main")


def test_sandboxed_run_scrubs_env(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    p = hooks.CommandPolicy(allow=["Bash(env)"])
    out = hooks.run_sandboxed("env", tmp_path, p).stdout
    assert "OPENAI_API_KEY" not in out and "PATH=" in out
    with pytest.raises(PermissionError):
        hooks.run_sandboxed("curl https://example.com", tmp_path, p)


def test_precommit_hook_blocks_a_secret(tmp_path):
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(tmp_path), *args], capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    hook = tmp_path / ".git" / "hooks" / "pre-commit"
    hook.write_text(f"#!/bin/sh\nexec python3 {HERE / 'precommit_secret_scan.py'}\n")
    hook.chmod(0o755)
    (tmp_path / "a.py").write_text("x = 1\n")
    git("add", "a.py")
    assert git("commit", "-qm", "ok").returncode == 0
    (tmp_path / "b.py").write_text('aws = "AKIA' + "Q" * 16 + '"\n')
    git("add", "b.py")
    blocked = git("commit", "-qm", "leak")
    assert blocked.returncode == 1 and "b.py:1: aws-access-key-id" in blocked.stderr
