import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from label_matcher import find_matching_labels

# PASS with bug (same case)

def test_exact_match():
    assert find_matching_labels(['bug', 'feature'], ['bug']) == ['bug']

def test_no_match():
    assert find_matching_labels(['feature'], ['bug']) == []

def test_multiple_matches():
    result = find_matching_labels(['bug', 'docs', 'feature'], ['bug', 'docs'])
    assert result == ['bug', 'docs']

def test_empty_labels():
    assert find_matching_labels([], ['bug']) == []

# FAIL with bug (case mismatch)

def test_uppercase_issue_label():
    result = find_matching_labels(['Bug'], ['bug'])
    assert result == ['Bug']  # bug: [] (case-sensitive miss)

def test_uppercase_filter_label():
    result = find_matching_labels(['bug'], ['Bug'])
    assert result == ['bug']  # bug: []

def test_mixed_case():
    result = find_matching_labels(['BUG', 'Feature'], ['bug', 'feature'])
    assert len(result) == 2  # bug: []
