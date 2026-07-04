import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pr_issue_finder import find_closing_issues

# --- PASS with bug (exact 'Closes' case or no keyword — both agree) ---

def test_closes_exact_case():
    assert find_closing_issues('Closes #42') == [42]

def test_no_closing_keyword():
    assert find_closing_issues('Fix typo in README') == []

def test_multiple_closes():
    assert find_closing_issues('Closes #1 and Closes #2') == [1, 2]

def test_closes_in_sentence():
    assert find_closing_issues('This PR Closes #99 and improves performance') == [99]

# --- FAIL with bug (lowercase/uppercase variants not matched) ---

def test_closes_lowercase():
    assert find_closing_issues('closes #42') == [42]

def test_closes_all_caps():
    assert find_closing_issues('CLOSES #7') == [7]

def test_closes_mid_sentence_lowercase():
    assert find_closing_issues('This PR closes #15 as requested') == [15]
