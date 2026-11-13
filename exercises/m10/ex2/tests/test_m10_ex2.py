import re
import shutil

import pytest
import skills
from _impl import variant_dir

SKILL = variant_dir(__file__) / "release-process"


class FakeRelease:
    def __init__(self) -> None:
        self.done: list[str] = []
        self.version = "1.3.2"
        self.changelog: list[str] = []
        self.tags: list[str] = []
        self.pushed = False

    def run(self, cmd: str) -> None:
        verb, *args = cmd.split()[1:]
        order = ["check-clean", "run-tests", "bump", "changelog", "tag", "push"]
        expected = order[len(self.done)] if len(self.done) < len(order) else None
        if verb != expected:
            raise RuntimeError(f"release {verb} out of order (expected {expected})")
        if verb == "bump":
            self.version = args[0]
        elif verb == "changelog":
            assert args[0] == self.version, "changelog version must match the bump"
            self.changelog.append(args[0])
        elif verb == "tag":
            assert args[0] == f"v{self.version}", "tag must be v<version>"
            self.tags.append(args[0])
        elif verb == "push":
            self.pushed = True
        self.done.append(verb)


def test_skill_is_valid():
    report = skills.validate_skill(SKILL)
    assert report.errors == []
    assert "description doesn't say when to use the skill" not in report.warnings


def test_agent_follows_the_skill(tmp_path):
    root = tmp_path / "skills"
    shutil.copytree(SKILL, root / SKILL.name)
    for other in ("release-notes",):  # a distractor the agent must not pick
        (root / other).mkdir()
        (root / other / "SKILL.md").write_text(
            "---\nname: release-notes\ndescription: Drafts release notes text from merged PRs. Use when asked for notes.\n---\nx\n"  # noqa: E501
        )
    catalog = skills.SkillCatalog(root)
    catalog.startup_prompt()
    chosen = catalog.choose("Cut release 1.4.0 of the app")
    assert chosen == SKILL.name
    body = catalog.activate(chosen)
    steps = [
        m.group(1)
        for line in body.splitlines()
        if (m := re.match(r"^\d+\.\s.*?`(release [^`]+)`", line))
    ]
    repo = FakeRelease()
    for step in steps:
        try:
            repo.run(step.replace("<version>", "1.4.0"))
        except RuntimeError as e:
            pytest.fail(str(e))
    assert (repo.version, repo.tags, repo.changelog, repo.pushed) == (
        "1.4.0",
        ["v1.4.0"],
        ["1.4.0"],
        True,
    )
