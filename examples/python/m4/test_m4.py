from pathlib import Path

import pytest
from compaction import compact, demo_conversation, pinned_lines, tokens
from context_budget import approx_tokens, build_context, truncate_to_tokens
from gui_context import (
    GEMINI_NANO_INPUT,
    HIGH_RES,
    LITERT_LM_A73,
    fit_screenshot,
    fit_small_window,
    prune_android,
    prune_dom,
    render_marks,
    to_device,
    visual_tokens,
)
from memory_store import MemoryStore
from repo_qa import BUDGET, ask, generate_codebase
from retrieval import BM25, TrigramIndex, chunk_lines, rerank, rrf, tokenize
from skills_loader import load_skill, savings

from aincourse import AssistantTurn, ScriptedModel

FIXTURE = Path(__file__).parent.parent / "m3" / "fixtures" / "login_screen.xml"


# ------------------------------------------------------------------ L4.1
def test_build_context_respects_budget_and_keeps_newest_history():
    history = [f"turn {i} " + "x" * 400 for i in range(40)]
    r = build_context("sys", "tools", ["doc " * 2000], history, budget=1500)
    assert r.tokens <= 1500
    assert r.dropped_history > 0
    assert "turn 39" in r.prompt and "turn 0 " not in r.prompt
    assert r.truncated_docs == 1


def test_fixed_part_over_budget_raises():
    with pytest.raises(ValueError):
        build_context("x" * 10_000, "", [], [], budget=100)


def test_truncation_marks_cut():
    out = truncate_to_tokens("a" * 1000, 50)
    assert out.endswith("…[truncated]") and approx_tokens(out) <= 50


# ------------------------------------------------------------------ L4.2
def test_compaction_shrinks_and_keeps_pins():
    convo = demo_conversation()
    summariser = ScriptedModel([AssistantTurn(text="We discussed the pipeline.")])
    short = compact(convo, summariser, keep_last=4)
    assert tokens(short) < tokens(convo) / 5
    assert short[0].role == "system"
    assert short[-4:] == convo[-4:]
    for pin in pinned_lines(convo):
        assert pin in short[1].content  # fidelity: decisions survive verbatim


# ------------------------------------------------------------------ L4.3
def test_memory_newer_fact_wins_and_persists(tmp_path):
    store = MemoryStore(tmp_path / "mem.json")
    store.remember("user.editor", "neovim", at=200)
    store.remember("user.editor", "vim", at=100)  # late-arriving older fact
    assert store.recall("user.editor") == "neovim"
    store.save()
    again = MemoryStore(tmp_path / "mem.json")
    assert again.recall("user.editor") == "neovim"
    assert len(again.search_episodes("editor")) == 2
    assert "as of 200" in again.as_context(["user.editor", "missing"])


# ------------------------------------------------------------------ L4.4
CODE = {
    "src/config.py": "def parse_config(path):\n    return load_yaml(path)\n" + "\n" * 50,
    "src/net.py": "def open_socket(host):\n    return connect(host)\n" + "\n" * 50,
    "docs/setup.md": "Run the parser on your config file before starting.\n",
}


def _chunks():
    return [c for p, t in CODE.items() for c in chunk_lines(p, t, size=20, overlap=5)]


def test_chunks_cite_lines_and_overlap():
    chunks = chunk_lines("a.py", "\n".join(f"l{i}" for i in range(1, 51)), size=20, overlap=5)
    assert [c.cite for c in chunks] == ["a.py:1-20", "a.py:16-35", "a.py:31-50"]


def test_tokenize_splits_identifiers():
    assert tokenize("parseConfig open_socket HTTPServer") == [
        "parse",
        "config",
        "open",
        "socket",
        "http",
        "server",
    ]


def test_bm25_finds_identifier_and_hybrid_keeps_it_first():
    chunks = _chunks()
    lexical = BM25(chunks).search("parse_config", k=3)
    assert lexical[0].path == "src/config.py"
    dense = TrigramIndex(chunks).search("parse_config", k=3)
    fused = rerank("parse_config", rrf([lexical, dense]))
    assert fused[0].cite.startswith("src/config.py:1-")


def test_bm25_returns_nothing_for_unknown_terms():
    assert BM25(_chunks()).search("kubernetes") == []


# ------------------------------------------------------------------ L4.5
def test_progressive_disclosure_saves_tokens():
    everything, disclosed = savings()
    assert disclosed < everything / 2
    assert "error" in load_skill("nope")


# ------------------------------------------------------------------ repo-QA WE
def test_repo_qa_stays_under_20k_tokens(tmp_path):
    assert generate_codebase(tmp_path) == 50_000
    r = ask(tmp_path, "Where is `parse_config` defined?")
    assert r.answer == "`parse_config` is defined at mod_37.py:991."
    assert r.max_prompt_tokens < BUDGET
    assert r.calls == 3


def test_repo_qa_unknown_symbol(tmp_path):
    generate_codebase(tmp_path, modules=3, lines_per_module=100)
    assert "not defined" in ask(tmp_path, "Where is `nope` defined?").answer


def test_repo_qa_grep_is_truncated(tmp_path):
    generate_codebase(tmp_path)
    r = ask(tmp_path, "Where is `handler_` defined?")  # thousands of hits
    assert r.max_prompt_tokens < BUDGET


# ------------------------------------------------------------------ GUI / on-device WE
def test_android_pruning_keeps_interactive_nodes_with_stable_ids():
    xml = FIXTURE.read_text()
    marks = prune_android(xml)
    assert [m.label for m in marks] == ["Username", "Sign in"]
    assert marks[1].center == (540, 1300)
    shifted = xml.replace("[340,1250][740,1350]", "[340,1310][740,1410]")
    assert prune_android(shifted)[1].id == marks[1].id  # layout shift keeps the id
    assert len(render_marks(marks)) < len(xml) / 5


def test_dom_pruning_skips_hidden_inputs():
    html = (
        '<div><h1>Shop</h1><input type="hidden" name="csrf"><input id="q" placeholder="Search">'
        '<button id="go">Search</button><a href="/cart">Cart</a><p>lots of text</p></div>'
    )
    assert [(m.role, m.label) for m in prune_dom(html)] == [
        ("input", "Search"),
        ("button", "Search"),
        ("link", "Cart"),
    ]


def test_visual_tokens_match_documented_examples():
    assert visual_tokens(200, 200) == 64
    assert visual_tokens(1000, 1000) == 1296
    assert visual_tokens(1092, 1092) == 1521


def test_fit_screenshot_and_map_back():
    w, h, s = fit_screenshot(1080, 2400)  # A73 portrait screen
    assert max(w, h) <= 1568 and visual_tokens(w, h) <= 1568
    assert to_device(round(540 * s), round(1300 * s), s) == pytest.approx((540, 1300), abs=2)
    w2, h2, _ = fit_screenshot(3840, 2160, HIGH_RES)
    assert max(w2, h2) <= 2576 and visual_tokens(w2, h2) <= 4784


def test_small_window_keeps_question_and_newest_turns():
    turns = [f"turn {i}: " + "words " * 60 for i in range(80)]
    for window in (LITERT_LM_A73, GEMINI_NANO_INPUT):
        prompt, dropped = fit_small_window(
            "You are a notes assistant.", "User prefers metric.", turns, "Q: total?", window
        )
        assert approx_tokens(prompt) <= window - 256
        assert prompt.endswith("Q: total?") and "turn 79" in prompt and dropped > 0
    with pytest.raises(ValueError):
        fit_small_window("s", "m " * 5000, [], "q", LITERT_LM_A73)
