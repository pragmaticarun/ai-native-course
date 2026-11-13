from _impl import load

impl = load(__file__)
A, B, C = 'open:{"f": "a"}', 'open:{"f": "b"}', 'grep:{"q": "x"}'


def test_same_call():
    assert impl.find_cycle([C, A, A, A]) == [A]


def test_two_step_cycle():
    assert impl.find_cycle([C, A, B, A, B, A, B]) == [A, B]
    assert impl.should_stop([A, B, A, B, A, B])


def test_three_step_cycle():
    assert impl.find_cycle([A, B, C] * 3) == [A, B, C]


def test_progress_is_not_a_cycle():
    assert impl.find_cycle([A, B, C, A, B]) is None
    assert impl.find_cycle([A, A]) is None
    assert not impl.should_stop([A, B, A, B, C])
