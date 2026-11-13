from _impl import load

impl = load(__file__)
BASE = {
    "sensitive": False,
    "online": True,
    "local_ok": True,
    "local_ctx": 4096,
    "est_tokens": 300,
    "hard": False,
}


def r(prompt, **kw):
    return impl.route(prompt, **(BASE | kw))


def test_pii_detection():
    assert impl.has_pii("write to priya@example.com")
    assert impl.has_pii("call +91 98765 43210 tomorrow")
    assert impl.has_pii("card 4111-1111-1111-1111")
    assert not impl.has_pii("meet at 10:30 in room 12")


def test_pii_stays_local_even_when_hard():
    assert r("summarise my chat with priya@example.com", hard=True) == "local"


def test_pii_refuses_rather_than_uploading():
    assert r("call +91 98765 43210", local_ok=False) == "refuse"
    assert r("my diagnosis notes", sensitive=True, est_tokens=9000) == "refuse"


def test_non_private_routes():
    assert r("summarise this public article", hard=True) == "cloud"
    assert r("tag this note") == "local"
    assert r("tag this note", local_ok=False) == "cloud"
    assert r("tag this note", online=False) == "local"
    assert r("long public doc", online=False, est_tokens=9000) == "refuse"
