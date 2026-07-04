import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pr_merger import can_merge_pr

# PASS with bug (uses 'approved' key correctly)

def test_approved_pr_mergeable():
    pr = {'approved': True, 'ci_passing': True, 'has_conflicts': False}
    assert can_merge_pr(pr) is True

def test_conflicts_blocks_merge():
    pr = {'approved': True, 'ci_passing': True, 'has_conflicts': True}
    assert can_merge_pr(pr) is False

def test_ci_failing_blocks_merge():
    pr = {'approved': True, 'ci_passing': False, 'has_conflicts': False}
    assert can_merge_pr(pr) is False

def test_not_approved_blocks_merge():
    pr = {'approved': False, 'ci_passing': True, 'has_conflicts': False}
    assert can_merge_pr(pr) is False

# FAIL with bug (correct key is 'review_approved', not 'approved')

def test_review_approved_basic():
    pr = {'review_approved': True, 'ci_passing': True, 'has_conflicts': False}
    assert can_merge_pr(pr) is True  # bug: 'approved' missing → False

def test_review_approved_with_extra_fields():
    pr = {'review_approved': True, 'ci_passing': True, 'has_conflicts': False, 'draft': False}
    assert can_merge_pr(pr) is True  # bug: False

def test_review_approved_second_reviewer():
    pr = {'review_approved': True, 'reviewer': 'alice', 'ci_passing': True, 'has_conflicts': False}
    assert can_merge_pr(pr) is True  # bug: False
