import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from permission_checker import user_has_permission

# --- PASS with bug (exact match or clearly below — both agree) ---

def test_exact_level_match():
    assert user_has_permission(3, 3) is True

def test_below_required():
    assert user_has_permission(1, 3) is False

def test_zero_vs_nonzero():
    assert user_has_permission(0, 2) is False

def test_max_exact_match():
    assert user_has_permission(5, 5) is True

# --- FAIL with bug (higher level than required: bug False, fix True) ---

def test_higher_level_grants_access():
    assert user_has_permission(4, 2) is True

def test_admin_has_write_permission():
    assert user_has_permission(5, 3) is True

def test_owner_has_read_permission():
    assert user_has_permission(10, 1) is True
