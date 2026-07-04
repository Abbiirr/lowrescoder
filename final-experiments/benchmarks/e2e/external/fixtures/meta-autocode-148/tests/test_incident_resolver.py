import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from incident_resolver import filter_high_severity

# PASS with bug (clearly above or clearly below threshold)

def test_empty_issues():
    assert filter_high_severity([], 5) == []

def test_clearly_above_threshold():
    issue = {'id': 1, 'severity': 10}
    result = filter_high_severity([issue], 5)
    assert result == [issue]  # 10 > 5 == True with both bug and fix

def test_clearly_below_threshold():
    issue = {'id': 1, 'severity': 2}
    result = filter_high_severity([issue], 5)
    assert result == []  # 2 > 5 == 2 >= 5 == False

def test_multiple_mixed():
    issues = [{'id': 1, 'severity': 8}, {'id': 2, 'severity': 3}, {'id': 3, 'severity': 9}]
    result = filter_high_severity(issues, 5)
    assert len(result) == 2  # ids 1 and 3 (8>5 and 9>5, also >=5)

# FAIL with bug (exactly at threshold must be included)

def test_exactly_at_threshold():
    issue = {'id': 1, 'severity': 5}
    result = filter_high_severity([issue], 5)
    assert result == [issue]  # bug: 5>5=False → []

def test_threshold_zero():
    issue = {'id': 1, 'severity': 0}
    result = filter_high_severity([issue], 0)
    assert result == [issue]  # bug: 0>0=False → []

def test_boundary_case():
    issues = [{'id': 1, 'severity': 3}, {'id': 2, 'severity': 4}]
    result = filter_high_severity(issues, 4)
    assert len(result) == 1 and result[0]['id'] == 2  # bug: only id=2 if 3>4 is False (correct), but 4>4 is False too!
