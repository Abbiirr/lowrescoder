import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from access_control import can_edit_memo

# PASS (bug and fix agree)

def test_owner_and_admin():
    assert can_edit_memo(1, 1, True) == True  # both: True and True / True or True

def test_non_owner_non_admin():
    assert can_edit_memo(2, 1, False) == False  # both: False

def test_different_ids_non_admin():
    assert can_edit_memo(3, 5, False) == False  # both: False

def test_total_stranger():
    assert can_edit_memo(99, 42, False) == False  # both: False

# FAIL (partial match — bug too strict)

def test_owner_not_admin():
    assert can_edit_memo(1, 1, False) == True  # bug: True and False = False

def test_admin_not_owner():
    assert can_edit_memo(2, 1, True) == True  # bug: False and True = False

def test_owner_of_own_memo():
    assert can_edit_memo(7, 7, False) == True  # bug: True and False = False
