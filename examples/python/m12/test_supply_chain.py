from __future__ import annotations

import json
import site
import sys
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import supply_chain as sc
import yaml

FIX = Path(__file__).parent / "fixtures" / "supply_chain"
REPO = Path(__file__).resolve().parents[3]


def test_agent_requirements_need_exact_pins_and_hashes():
    found = [str(f) for f in sc.audit_requirements((FIX / "requirements-agent.txt").read_text())]
    assert found == [
        "agent-framework: not an exact pin (>=1.26)",
        "agent-framework: no --hash=sha256 (install with --require-hashes)",
        "pydantic-ai-slim: no --hash=sha256 (install with --require-hashes)",
        "requests: not an exact pin (no version)",
        "requests: no --hash=sha256 (install with --require-hashes)",
    ]  # langgraph (hash on a continuation line) and pyyaml pass


def test_known_compromised_release_is_flagged_even_when_pinned_and_hashed():
    line = "agent-framework==1.26.2 --hash=sha256:" + "a" * 64
    assert [str(f) for f in sc.audit_requirements(line)] == [
        "agent-framework: known-compromised release 1.26.2"
    ]
    assert sc.audit_requirements("agent-framework==1.26.0 --hash=sha256:" + "b" * 64) == []


def test_startup_hooks_path_lines_are_fine_import_lines_and_start_files_are_not(tmp_path):
    (tmp_path / "_editable_impl_pkg.pth").write_text("/src/pkg\n")  # path only: never executed
    (tmp_path / "agent_framework_meta.pth").write_text("import agent_framework_meta\n")
    (tmp_path / "telemetry.pth").write_text(
        "# comment\nimport telemetry_boot; telemetry_boot.go()\n"
    )
    (tmp_path / "tool.start").write_text("# Python 3.15 entry points\ntool.boot:main\n")
    found = [str(f) for f in sc.scan_startup_hooks(tmp_path)]
    assert found == [
        "agent_framework_meta.pth: known indicator of compromise (agent-framework)",
        "telemetry.pth: runs at every Python start: 'import telemetry_boot; telemetry_boot.go()'",
        "tool.start: runs at every Python start: 'tool.boot:main'",
    ]
    # A reviewed hook can be allowlisted by file name; an IOC cannot.
    allow = frozenset({"telemetry.pth", "tool.start", "agent_framework_meta.pth"})
    assert [f.where for f in sc.scan_startup_hooks(tmp_path, allow)] == ["agent_framework_meta.pth"]


def test_the_course_venv_has_no_startup_hooks():
    """Real check on the environment running this test (uv's venv in CI and on the box)."""
    dirs = {
        Path(p) for p in [*site.getsitepackages(), site.getusersitepackages()] if Path(p).is_dir()
    }
    # setuptools' distutils shim is a well-known, reviewed hook; nothing else is expected.
    allow = frozenset({"distutils-precedence.pth"})
    found = [f"{d}: {f}" for d in sorted(dirs) for f in sc.scan_startup_hooks(d, allow)]
    assert found == [], f"unexpected startup hooks under {sys.prefix}: {found}"


def test_a_one_day_cooldown_would_have_skipped_the_poisoned_releases():
    raw = json.loads((FIX / "release_times.json").read_text())
    times = {
        tuple(k.split("==")): datetime.fromisoformat(v)
        for k, v in raw.items()
        if not k.startswith("_")
    }
    uploaded = {(n, v): t for (n, v), t in times.items()}
    # 30 minutes after 1.26.2 appeared, an agent "upgrades to latest".
    now = datetime(2026, 11, 17, 21, 38, tzinfo=UTC)
    assert [
        str(f) for f in sc.cooldown_violations({"agent-framework": "1.26.2"}, uploaded, now)
    ] == ["agent-framework==1.26.2: only 0.5 h old"]
    assert sc.cooldown_violations({"agent-framework": "1.26.0"}, uploaded, now) == []
    unknown = sc.cooldown_violations({"agent-framwork": "1.26.0"}, uploaded, now)  # typosquat-ish
    assert "upload time unknown" in unknown[0].problem
    week = timedelta(days=7)  # pnpm's suggested stricter setting (10080 minutes)
    late = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)
    pins = {"pydantic-ai-slim": "2.71.0", "langgraph": "1.2.24"}
    assert [f.where for f in sc.cooldown_violations(pins, uploaded, late, week)] == [
        "langgraph==1.2.24",
        "pydantic-ai-slim==2.71.0",
    ]
    assert sc.cooldown_violations(pins, uploaded, late) == []


def test_workflow_tokens_split_install_from_token_minting():
    risky = yaml.safe_load((FIX / "workflow-risky.yml").read_text())
    assert [str(f) for f in sc.workflow_token_findings(risky)] == [
        "workflow: no top-level permissions: GITHUB_TOKEN gets defaults",
        "jobs.deploy: can mint OIDC tokens and runs 'pip install -r requirements.txt'",
    ]
    split = yaml.safe_load((FIX / "workflow-split.yml").read_text())
    assert sc.workflow_token_findings(split) == []
    # Top-level id-token: write reaches a build job that has no permissions of its own.
    inherited = {
        "permissions": {"contents": "read", "id-token": "write"},
        "jobs": {"build": {"steps": [{"uses": "withastro/action@v6"}]}},
    }
    assert [str(f) for f in sc.workflow_token_findings(inherited)] == [
        "workflow: top-level write permissions {'contents': 'read', 'id-token': 'write'}",
        "jobs.build: can mint OIDC tokens and runs 'withastro/action'",
    ]


@pytest.mark.parametrize("wf", sorted((REPO / ".github" / "workflows").glob("*.yml")))
def test_this_repos_workflows_pass(wf):
    assert sc.workflow_token_findings(yaml.safe_load(wf.read_text())) == []


def test_this_repo_practices_what_the_lesson_teaches():
    py = tomllib.loads((REPO / "python" / "pyproject.toml").read_text())
    assert py["tool"]["uv"]["exclude-newer"] == "1 day"
    for dep in py["project"]["dependencies"]:
        assert "==" in dep, dep
    lock = tomllib.loads((REPO / "python" / "uv.lock").read_text())
    for pkg in lock["package"]:
        if "registry" not in pkg.get("source", {}):
            continue  # the course package itself (editable)
        files = pkg.get("wheels", []) + ([pkg["sdist"]] if "sdist" in pkg else [])
        assert files and all(f["hash"].startswith("sha256:") for f in files), pkg["name"]
    for ws in ("pnpm-workspace.yaml", "site/pnpm-workspace.yaml"):
        assert yaml.safe_load((REPO / ws).read_text())["minimumReleaseAge"] >= 1440, ws
