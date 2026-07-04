import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from ref_checker import is_tag_ref

# PASS (non-tag refs — both return False)

def test_branch_ref():
    assert is_tag_ref('refs/heads/main') == False

def test_remote_ref():
    assert is_tag_ref('refs/remotes/origin/main') == False

def test_empty_string():
    assert is_tag_ref('') == False

def test_no_refs_prefix():
    assert is_tag_ref('tags/v1.0.0') == False  # missing 'refs/' prefix

# FAIL (valid tag refs — bug: False, fix: True)

def test_version_tag():
    assert is_tag_ref('refs/tags/v1.0.0') == True  # bug: 'refs/tag/' not in prefix

def test_latest_tag():
    assert is_tag_ref('refs/tags/latest') == True  # bug: returns False

def test_release_tag():
    assert is_tag_ref('refs/tags/release-2024') == True  # bug: returns False
