import random


def test_pick():
    rng = random.Random(42)
    random.seed(1)
    assert rng.choice([1, 2]) in (1, 2)
