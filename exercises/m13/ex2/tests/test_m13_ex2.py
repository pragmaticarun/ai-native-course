import json
from pathlib import Path

import pytest
from _impl import load

impl = load(__file__)
ROWS = json.loads((Path(__file__).parent / "box_llama_b12359.json").read_text())["rows"]


def q(rows):
    return [r["quant"] for r in rows]


def test_pareto_on_the_box_table():
    # Nothing dominates anything here: F32 wins quality, Q4_0 wins size and speed,
    # Q8_0 and Q4_K_M each trade one for another.
    assert q(impl.pareto(ROWS)) == ["F32", "Q8_0", "Q4_K_M", "Q4_0"]


def test_pareto_with_a_dominated_row():
    worse = {"quant": "BAD", "size_mb": 30.0, "mean_kld": 0.2, "tg_tps": 1000.0}
    assert "BAD" not in q(impl.pareto([*ROWS, worse]))
    assert q(impl.pareto([ROWS[1], ROWS[1] | {"quant": "SAME"}])) == ["Q8_0", "SAME"]


def test_pick():
    assert impl.pick(ROWS, max_mb=30, max_kld=0.01)["quant"] == "Q8_0"
    assert impl.pick(ROWS, max_mb=22, max_kld=0.05)["quant"] == "Q4_K_M"
    assert impl.pick(ROWS, max_mb=25, max_kld=0.2)["quant"] == "Q4_0"
    assert impl.pick(ROWS, max_mb=10, max_kld=1.0) is None


def test_kv_cache():
    # stories15M: 6 layers, 6 KV heads x 48; F16 cache, 128 positions
    assert impl.kv_cache_mb(6, 128, 6, 48, 2) == pytest.approx(0.884736)
    # a hypothetical small model at 4k context: 1 KV head (MQA) is what keeps this small
    assert impl.kv_cache_mb(26, 4096, 1, 256, 2) == pytest.approx(109.051904)
