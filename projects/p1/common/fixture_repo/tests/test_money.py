from textkit.money import apply_discount, split_bill


def test_discount():
    assert apply_discount(1000, 15) == 850
    assert apply_discount(999, 0) == 999


def test_split_bill():
    assert split_bill(1000, 3) == [334, 333, 333]
    assert split_bill(1001, 3) == [334, 334, 333]
    assert split_bill(900, 3) == [300, 300, 300]
    assert sum(split_bill(1234, 5)) == 1234
