from _impl import load

impl = load(__file__)
OK = dict.fromkeys(
    [
        "tests-with-code",
        "pinned-deps",
        "todo-has-issue",
        "reversible-migration",
        "no-deleted-tests",
    ],
    True,
)

PR1 = impl.PR(  # clean: thumbnails tool with tests and an exact pin
    files={
        "src/thumbs.py": "def thumbnails(path, n):\n    # TODO(#41): seek by keyframe\n    ...",
        "tests/test_thumbs.py": "def test_count():\n    assert len(thumbnails('a.mp4', 3)) == 3",
        "pyproject.toml": '  "av==19.0.2",',
    }
)
PR2 = impl.PR(  # the classic agent PR: code, a loose pin, a bare TODO, no tests
    files={
        "src/loud.py": "def loudness(p):\n    # TODO handle mono\n    ...",
        "package.json": '    "ffmpeg-static": "^5.2.0",',
    }
)
PR3 = impl.PR(  # a migration with no way back, and a deleted flaky test
    files={
        "migrations/0007_add_index.py": "def upgrade(op):\n    op.create_index('ix_clip', 'clips', ['path'])",  # noqa: E501
        "tests/test_store.py": "def test_insert():\n    assert store.insert(x)",
    },
    deleted=["tests/test_flaky_upload.py"],
)


def test_clean_pr():
    assert impl.apply(PR1) == OK


def test_classic_agent_pr():
    assert impl.apply(PR2) == {
        **OK,
        "tests-with-code": False,
        "pinned-deps": False,
        "todo-has-issue": False,
    }


def test_migration_pr():
    assert impl.apply(PR3) == {**OK, "reversible-migration": False, "no-deleted-tests": False}


def test_pin_styles():
    for loose in [
        '"httpx>=0.27",',
        "numpy~=2.1",
        '"zod": "~4.6.7",',
        "pydantic>2",
        '"left-pad": "*",',
    ]:
        assert not impl.pinned_deps(impl.PR(files={"requirements-dev.txt": loose})), loose
    for exact in ['"httpx==0.28.1",', '"zod": "4.6.7",']:
        assert impl.pinned_deps(impl.PR(files={"package.json": exact})), exact
