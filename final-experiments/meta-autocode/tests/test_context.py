"""Tests for ProgressiveContextLoader — meta-autocode Phase 2.

Design goal: beat Codex 61.5% by loading the most relevant files first.
65% of harness failures come from environment/context setup issues (arxiv 2508.18993).
Loading test files first (they encode intent) then ranked source files cuts this failure mode.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from meta_autocode.context import ProgressiveContextLoader, FileEntry


def _make_loader(files: dict[str, str]) -> ProgressiveContextLoader:
    return ProgressiveContextLoader(files)


def test_test_files_ranked_first():
    files = {
        "src/main.py": "def run(): pass",
        "tests/test_main.py": "def test_run(): assert run() is None",
        "README.md": "# project",
    }
    loader = _make_loader(files)
    ranked = loader.rank(query="run function")
    paths = [e.path for e in ranked]
    assert paths[0] == "tests/test_main.py", "test files must come first"


def test_returns_file_entries():
    files = {"src/a.py": "def foo(): pass"}
    loader = _make_loader(files)
    ranked = loader.rank(query="foo")
    assert len(ranked) == 1
    entry = ranked[0]
    assert isinstance(entry, FileEntry)
    assert entry.path == "src/a.py"
    assert isinstance(entry.score, float)
    assert entry.content == "def foo(): pass"


def test_score_reflects_query_relevance():
    files = {
        "src/parser.py": "def parse_date(s): return datetime.fromisoformat(s)",
        "src/utils.py": "def clamp(v, lo, hi): return max(lo, min(hi, v))",
    }
    loader = _make_loader(files)
    ranked = loader.rank(query="parse date")
    assert ranked[0].path == "src/parser.py", "higher relevance file must rank first"
    assert ranked[0].score > ranked[1].score


def test_empty_files_returns_empty():
    loader = _make_loader({})
    assert loader.rank(query="anything") == []


def test_single_file_always_returned():
    loader = _make_loader({"src/x.py": "x = 1"})
    ranked = loader.rank(query="unrelated query xyz")
    assert len(ranked) == 1
    assert ranked[0].path == "src/x.py"


def test_token_budget_truncates():
    big = "word " * 2000  # ~10k chars
    files = {f"src/f{i}.py": big for i in range(10)}
    loader = _make_loader(files)
    ranked = loader.rank(query="word", token_budget=500)
    # With a budget of 500 tokens (~2000 chars), fewer than 10 files should survive
    assert len(ranked) < 10


def test_test_file_boost_is_documented():
    # The boost factor for test files must be a class attribute, not a magic number
    assert hasattr(ProgressiveContextLoader, "TEST_BOOST"), \
        "ProgressiveContextLoader.TEST_BOOST must be a class attribute"
    assert ProgressiveContextLoader.TEST_BOOST > 1.0, "TEST_BOOST must be > 1.0"


def test_rank_stable_across_calls():
    files = {
        "tests/test_a.py": "def test_alpha(): pass",
        "src/alpha.py": "def alpha(): return 1",
        "src/beta.py": "def beta(): return 2",
    }
    loader = _make_loader(files)
    r1 = loader.rank(query="alpha")
    r2 = loader.rank(query="alpha")
    assert [e.path for e in r1] == [e.path for e in r2], "rank must be deterministic"
