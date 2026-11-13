from _impl import load

impl = load(__file__)
OLD = "replicas: 2\nimage: app:1.4\n"
NEW = "replicas: 6\nimage: app:1.5\nfeature_flag: on\n"


def test_request_has_diff_summary_and_hash():
    r = impl.make_request(OLD, NEW, "deploy", "agent")
    assert "-replicas: 2" in r.diff and "+feature_flag: on" in r.diff
    assert r.summary == "+3 -2 lines"
    assert len(r.diff_hash) == 64


def test_rubber_stamps_are_rejected():
    r = impl.make_request(OLD, NEW, "deploy", "agent")
    assert impl.accept(r, impl.Decision(True, "arun", "ok", r.diff_hash)) is not None
    assert impl.accept(r, impl.Decision(True, "agent", "I checked it all", r.diff_hash)) is not None
    stale = impl.make_request(OLD, "replicas: 3\n", "deploy", "agent")
    assert (
        impl.accept(r, impl.Decision(True, "arun", "checked replicas and image", stale.diff_hash))
        is not None
    )


def test_real_review_passes():
    r = impl.make_request(OLD, NEW, "deploy", "agent")
    assert (
        impl.accept(r, impl.Decision(True, "arun", "checked replicas and image tag", r.diff_hash))
        is None
    )
    assert impl.accept(r, impl.Decision(False, "arun", "", "")) is None
