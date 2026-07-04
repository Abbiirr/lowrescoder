import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from repo_checker import is_repo_archived

# PASS (no 'archived' or it is falsy — both bug and fix return False)

def test_empty():
    assert is_repo_archived({}) is False

def test_no_archive_key():
    assert is_repo_archived({'name': 'myrepo'}) is False

def test_archived_false():
    assert is_repo_archived({'archived': False}) is False

def test_archived_zero():
    assert is_repo_archived({'archived': 0}) is False

# FAIL ('archived' truthy — bug reads wrong key and returns False)

def test_archived_true():
    assert is_repo_archived({'archived': True}) is True  # bug: False

def test_archived_with_name():
    assert is_repo_archived({'archived': True, 'name': 'oldrepo'}) is True  # bug: False

def test_archived_one():
    assert is_repo_archived({'archived': 1}) is True  # bug: False
