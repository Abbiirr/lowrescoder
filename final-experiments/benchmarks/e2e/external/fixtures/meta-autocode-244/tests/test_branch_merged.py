import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from branch_merged import is_branch_merged

# PASS with bug (no 'merged' key or 'merged': False — both return False)
def test_empty():
    assert is_branch_merged({}) == False

def test_no_merged_key():
    assert is_branch_merged({'name': 'feature'}) == False

def test_remote_key():
    assert is_branch_merged({'remote': 'origin'}) == False

def test_merged_false():
    assert is_branch_merged({'merged': False}) == False

# FAIL with bug (has 'merged': True — bug reads 'is_merged', returns False)
def test_merged_true():
    assert is_branch_merged({'merged': True}) == True

def test_merged_with_name():
    assert is_branch_merged({'merged': True, 'name': 'feature'}) == True

def test_merged_with_remote():
    assert is_branch_merged({'merged': True, 'remote': 'origin'}) == True
