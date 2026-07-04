"""Tests for paginator — inspired by memos/gitea pagination patterns.

Off-by-one in pagination is a classic harness-bench v2 style bug: simple,
localized, and caught immediately by a test that checks page 1 content.
Codex xhigh (81.5%) solves most of these; this tests our harness handles it.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_first_page_starts_at_zero():
    from paginator import paginate
    items = list(range(10))
    result = paginate(items, page=1, per_page=3)
    assert result == [0, 1, 2], f"page 1 should be [0,1,2], got {result}"


def test_second_page():
    from paginator import paginate
    items = list(range(10))
    result = paginate(items, page=2, per_page=3)
    assert result == [3, 4, 5], f"page 2 should be [3,4,5], got {result}"


def test_third_page():
    from paginator import paginate
    items = list(range(10))
    result = paginate(items, page=3, per_page=3)
    assert result == [6, 7, 8], f"page 3 should be [6,7,8], got {result}"


def test_last_partial_page():
    from paginator import paginate
    items = list(range(10))
    result = paginate(items, page=4, per_page=3)
    assert result == [9], f"page 4 (partial) should be [9], got {result}"


def test_empty_list():
    from paginator import paginate
    assert paginate([], page=1, per_page=5) == []


def test_single_item():
    from paginator import paginate
    assert paginate(["only"], page=1, per_page=10) == ["only"]


def test_total_pages():
    from paginator import total_pages
    assert total_pages(10, 3) == 4
    assert total_pages(9, 3) == 3
    assert total_pages(0, 3) == 0
