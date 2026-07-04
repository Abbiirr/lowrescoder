"""Tests for memo_search — inspired by usememos/memos search.

Memos search should be case-insensitive so users find content regardless of
how they typed it. The bug uses `in` (case-sensitive), so searching "PYTHON"
won't find a memo containing "python".
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_exact_match():
    from memo_search import search_memo
    assert search_memo("meeting notes for today", "meeting") is True


def test_no_match():
    from memo_search import search_memo
    assert search_memo("buy groceries", "python") is False


def test_empty_query_matches_all():
    from memo_search import search_memo
    assert search_memo("any content here", "") is True


def test_substring_match():
    from memo_search import search_memo
    assert search_memo("scheduled for tomorrow morning", "tomorrow") is True


def test_uppercase_query_finds_lowercase_content():
    from memo_search import search_memo
    # Bug: "PYTHON" not in "python project notes" → False; expected True
    result = search_memo("python project notes", "PYTHON")
    assert result is True, f"expected True (case-insensitive), got {result}"


def test_lowercase_query_finds_uppercase_content():
    from memo_search import search_memo
    # Bug: "meeting" not in "Team Meeting Summary" → False; expected True
    result = search_memo("Team Meeting Summary", "meeting")
    assert result is True, f"expected True (case-insensitive), got {result}"


def test_mixed_case_query_and_content():
    from memo_search import search_memo
    # Bug: "Todo" not in "TODO list for sprint" → False; expected True
    result = search_memo("TODO list for sprint", "Todo")
    assert result is True, f"expected True (case-insensitive), got {result}"
