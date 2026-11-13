from textkit.seqs import chunk, dedupe, top_k


def test_chunk():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert chunk([], 3) == []


def test_top_k():
    assert top_k([3, 9, 1, 7], 2) == [9, 7]


def test_dedupe_keeps_order():
    assert dedupe(["b", "a", "b", "c", "a"]) == ["b", "a", "c"]
