import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from role_checker import is_admin

# PASS (explicit admin or clearly non-admin — bug and fix agree)

def test_admin_role():
    assert is_admin({'role': 'admin'}) == True

def test_member_role():
    assert is_admin({'role': 'member'}) == False

def test_viewer_role():
    assert is_admin({'role': 'viewer'}) == False

def test_no_role():
    assert is_admin({}) == False

# FAIL (owner role — bug returns False, fix returns True)

def test_owner_role():
    assert is_admin({'role': 'owner'}) == True  # bug: False

def test_owner_with_username():
    assert is_admin({'role': 'owner', 'username': 'alice'}) == True  # bug: False

def test_owner_with_id():
    assert is_admin({'id': 5, 'role': 'owner'}) == True  # bug: False
