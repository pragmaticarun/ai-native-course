import json

from _impl import load

impl = load(__file__)

FULL = '{"title": "Rust meetup", "tags": ["rust", "async"], "attendees": 42, "online": false}'


def test_progressive_prefixes_never_crash_and_grow():
    seen = []
    for i in range(1, len(FULL) + 1):
        out = impl.parse_partial(FULL[:i])
        assert isinstance(out, dict)
        seen.append(out)
    assert seen[-1] == json.loads(FULL)


def test_open_string_and_array():
    assert impl.parse_partial('{"title": "Rust me') == {"title": "Rust me"}
    assert impl.parse_partial('{"title": "x", "tags": ["rust", "as') == {
        "title": "x",
        "tags": ["rust", "as"],
    }


def test_dangling_key_and_trailing_comma():
    assert impl.parse_partial('{"a": 1, "b"') == {"a": 1}
    assert impl.parse_partial('{"a": 1,') == {"a": 1}
    assert impl.parse_partial('{"a": 1, "b":') == {"a": 1}


def test_nothing_yet():
    assert impl.parse_partial("") == {}
    assert impl.parse_partial("{") == {}
