import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from ref_parser import branch_from_ref

# PASS (simple single-segment branch names — bug and fix agree)

def test_main():
    assert branch_from_ref('refs/heads/main') == 'main'

def test_develop():
    assert branch_from_ref('refs/heads/develop') == 'develop'

def test_release():
    assert branch_from_ref('refs/heads/release') == 'release'

def test_hotfix():
    assert branch_from_ref('refs/heads/hotfix') == 'hotfix'

# FAIL (nested branch names — bug returns only last segment)

def test_feature_branch():
    assert branch_from_ref('refs/heads/feature/my-branch') == 'feature/my-branch'  # bug: 'my-branch'

def test_bugfix_branch():
    assert branch_from_ref('refs/heads/bugfix/issue-123') == 'bugfix/issue-123'  # bug: 'issue-123'

def test_deep_branch():
    assert branch_from_ref('refs/heads/user/john/task') == 'user/john/task'  # bug: 'task'
