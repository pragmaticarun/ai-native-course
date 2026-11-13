import random


def test_shuffle():
    random.seed(7)
    assert sorted(random.sample(range(5), 5)) == [0, 1, 2, 3, 4]
