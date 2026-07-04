import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from memo_filter import filter_memos

def memo(archived=False):
    return {'content': 'note', 'archived': archived}

# --- PASS with bug (include_archived=True or no archived memos) ---

def test_include_archived_returns_all():
    memos = [memo(False), memo(True)]
    assert filter_memos(memos, include_archived=True) == memos

def test_no_archived_memos_unchanged():
    memos = [memo(False), memo(False)]
    result = filter_memos(memos, include_archived=False)
    assert len(result) == 2

def test_empty_list():
    assert filter_memos([], include_archived=False) == []

def test_single_non_archived():
    memos = [memo(False)]
    assert filter_memos(memos) == memos

# --- FAIL with bug (archived present, include_archived=False — bug includes all) ---

def test_archived_excluded_by_default():
    memos = [memo(True)]
    result = filter_memos(memos)
    assert result == []

def test_mixed_archived_excluded():
    memos = [memo(False), memo(True)]
    result = filter_memos(memos)
    assert len(result) == 1
    assert result[0]['archived'] is False

def test_all_archived_returns_empty():
    memos = [memo(True), memo(True)]
    result = filter_memos(memos)
    assert result == []
