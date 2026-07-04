import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from issue_linker import extract_issue_refs

# PASS with bug (uses 'Fixes' keyword)

def test_fixes_keyword():
    assert extract_issue_refs('Fixes #123') == [123]

def test_fixes_case_insensitive():
    assert extract_issue_refs('fixes #99') == [99]

def test_multiple_fixes():
    assert extract_issue_refs('Fixes #1 and Fixes #2') == [1, 2]

def test_no_match_returns_empty():
    assert extract_issue_refs('relates to #50') == []

# FAIL with bug (Closes/Resolves/Fix not matched)

def test_closes_keyword():
    assert extract_issue_refs('Closes #200') == [200]  # bug: []

def test_resolves_keyword():
    assert extract_issue_refs('Resolves #300') == [300]  # bug: []

def test_fix_keyword_singular():
    assert extract_issue_refs('Fix #42') == [42]  # bug: []
