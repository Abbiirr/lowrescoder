import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from permission_checker import has_permission

# PASS with bug (single permission or all match — any() == all() in these cases)

def test_no_permissions_required():
    user = {'permissions': ['read', 'write']}
    assert has_permission(user, []) is False  # any([]) == all([]) == False

def test_single_permission_match():
    user = {'permissions': ['read', 'write']}
    assert has_permission(user, ['read']) is True

def test_all_permissions_present():
    user = {'permissions': ['read', 'write', 'delete']}
    assert has_permission(user, ['read', 'write']) is True

def test_no_user_permissions():
    user = {'permissions': []}
    assert has_permission(user, ['admin']) is False

# FAIL with bug (partial permission match should be denied — any() returns True, all() returns False)

def test_has_first_not_second():
    user = {'permissions': ['read']}
    # Bug: any(['read' in {'read'}]) = True; correct: all needs 'write' too
    assert has_permission(user, ['read', 'write']) is False

def test_has_last_not_first():
    user = {'permissions': ['write']}
    # Bug: any(['write' in {'write'}]) = True (write matches); correct: also needs 'read'
    assert has_permission(user, ['read', 'write']) is False

def test_one_of_three_missing():
    user = {'permissions': ['read', 'write']}
    # Bug: any() = True; correct: all() needs 'admin' too
    assert has_permission(user, ['read', 'write', 'admin']) is False
