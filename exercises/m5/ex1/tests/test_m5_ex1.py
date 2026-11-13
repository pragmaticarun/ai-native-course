from _impl import load

impl = load(__file__)
Step = impl.Step

TOOLS = {
    "probe": lambda path: "h264 1080p",
    "transcode": lambda path, codec: (
        f"{path}.{codec}" if codec != "av1" else "warning: av1 unsupported, nothing written"
    ),
    "upload": lambda path: f"uploaded {path}",
}


def test_unexpected_output_triggers_replan():
    plan = [
        Step("probe", {"path": "c"}, "h264"),
        Step("transcode", {"path": "c", "codec": "av1"}, "c.av1"),
        Step("upload", {"path": "c.av1"}, "uploaded"),
    ]
    seen = []

    def replan(executed, failure):
        seen.append((executed, failure))
        return [
            Step("transcode", {"path": "c", "codec": "hevc"}, "c.hevc"),
            Step("upload", {"path": "c.hevc"}, "uploaded"),
        ]

    r = impl.execute(plan, TOOLS, replan)
    assert r.done and r.replans == 1
    assert r.executed == ["h264 1080p", "c.hevc", "uploaded c.hevc"]
    assert seen[0][0] == ["h264 1080p"] and "transcode" in seen[0][1]


def test_exception_triggers_replan_and_budget_is_respected():
    def boom(**kw):
        raise RuntimeError("disk full")

    plan = [Step("boom", {}, "ok")]
    r = impl.execute(plan, {"boom": boom}, lambda e, f: [Step("boom", {}, "ok")], max_replans=2)
    assert not r.done and r.replans == 2 and r.executed == []


def test_happy_path_no_replan():
    r = impl.execute([Step("probe", {"path": "c"}, "h264")], TOOLS, lambda e, f: [])
    assert r.done and r.replans == 0 and r.executed == ["h264 1080p"]
