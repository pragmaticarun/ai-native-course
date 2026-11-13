from _impl import load

impl = load(__file__)


def fake_model(prompt: str) -> str:
    """Echoes the payload after the role prefix, like a perfectly obedient model."""
    return prompt.split(": ", 1)[1]


CASES = [
    ["AV1 decode", "HDR tone mapping", "crash fix", "faster seek"],
    ["Opus 48 kHz", "loudness -16 LUFS"],
]


def test_single_agent_is_one_call_with_all_facts():
    text, calls = impl.single_agent(CASES[0], fake_model)
    assert calls == 1 and impl.score(text, CASES[0]) == 1.0


def test_score():
    assert impl.score("av1 decode and crash fix", CASES[0]) == 0.5


def test_compare_shows_the_downgrade_wins():
    r = impl.compare(CASES, fake_model)
    assert r["three_agent"] == {"score": (0.75 + 1.0) / 2, "calls": 6}
    assert r["single_agent"] == {"score": 1.0, "calls": 2}
