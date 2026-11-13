import json
from pathlib import Path

import pytest
from _impl import load

impl = load(__file__)
RUNS = json.loads((Path(__file__).parent / "asr_runs.json").read_text())["runs"]


def test_wer_counts_all_edit_types():
    assert impl.wer("the cat sat", "the cat sat") == 0
    assert impl.wer("the cat sat", "the bat sat") == pytest.approx(1 / 3)  # substitution
    assert impl.wer("the cat sat", "the sat") == pytest.approx(1 / 3)  # deletion
    assert impl.wer("the cat sat", "the big cat sat") == pytest.approx(1 / 3)  # insertion
    assert impl.wer("Hello, World!", "hello world") == 0  # normalisation
    assert impl.wer("", "") == 0 and impl.wer("", "noise") == 1


def test_corpus_wer_is_word_weighted():
    pairs = [
        ("yes", "no"),
        (
            "one two three four five six seven eight nine",
            "one two three four five six seven eight nine",
        ),
    ]
    assert impl.corpus_wer(pairs) == pytest.approx(0.1)


def test_choose():
    assert impl.choose(RUNS, max_wer=0.10, max_rtf=1.0)["model"] == "base"
    assert impl.choose(RUNS, max_wer=0.0, max_rtf=1.0)["model"] == "small"
    assert impl.choose(RUNS, max_wer=0.5, max_rtf=1.0)["model"] == "tiny"
    assert impl.choose(RUNS, max_wer=0.0, max_rtf=0.2) is None
