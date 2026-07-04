import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from repo_stats import get_top_contributors

# PASS (n=0 or single contributor where order doesn't matter)

def test_no_commits():
    assert get_top_contributors([], 3) == []

def test_n_zero():
    commits = [{'author': 'alice'}, {'author': 'alice'}]
    assert get_top_contributors(commits, 0) == []

def test_single_author():
    commits = [{'author': 'alice'}, {'author': 'alice'}]
    assert get_top_contributors(commits, 1) == ['alice']  # only one author

def test_all_authors_equal_commits():
    commits = [{'author': 'a'}, {'author': 'b'}, {'author': 'c'}]
    result = get_top_contributors(commits, 3)
    assert set(result) == {'a', 'b', 'c'}  # order varies, but all 3 returned

# FAIL (clear winner is picked last by bug)

def test_top_1_of_3():
    commits = [{'author': 'alice'}] * 5 + [{'author': 'bob'}] * 2 + [{'author': 'carol'}]
    result = get_top_contributors(commits, 1)
    assert result == ['alice']  # bug: ascending → ['carol'] (least commits)

def test_top_2_of_3():
    commits = [{'author': 'alice'}] * 10 + [{'author': 'bob'}] * 3 + [{'author': 'carol'}]
    result = get_top_contributors(commits, 2)
    assert set(result) == {'alice', 'bob'}  # bug: {'carol', 'bob'} (wrong 2)

def test_top_1_two_authors():
    commits = [{'author': 'dave'}] * 7 + [{'author': 'eve'}] * 2
    result = get_top_contributors(commits, 1)
    assert result == ['dave']  # bug: ascending → ['eve'] (2 commits, least)
