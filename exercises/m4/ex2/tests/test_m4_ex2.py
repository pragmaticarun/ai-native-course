from _impl import load

impl = load(__file__)
DAY = 86_400


def test_out_of_order_facts_do_not_overwrite():
    s = impl.MemoryStore()
    s.remember("device", "Galaxy A73", at=10 * DAY)
    s.remember("device", "Pixel 4a", at=2 * DAY)
    assert s.recall("device", now=11 * DAY, max_age=30 * DAY) == "Galaxy A73"


def test_recall_hides_stale_facts():
    s = impl.MemoryStore()
    s.remember("android_version", "14", at=0)
    assert s.recall("android_version", now=10 * DAY, max_age=30 * DAY) == "14"
    assert s.recall("android_version", now=40 * DAY, max_age=30 * DAY) is None
    assert s.recall("nope", now=0, max_age=1) is None


def test_audit_catches_stale_wrong_and_missing():
    s = impl.MemoryStore()
    s.remember("device", "Galaxy A73", at=95 * DAY)
    s.remember("android_version", "14", at=0)  # updated since; memory is old
    s.remember("editor", "vim", at=99 * DAY)  # fresh but wrong
    truth = {"device": "Galaxy A73", "android_version": "16", "editor": "neovim", "shell": "bash"}
    assert impl.audit(s, truth, now=100 * DAY, max_age=30 * DAY) == {
        "stale": ["android_version"],
        "wrong": ["editor"],
        "missing": ["shell"],
    }
