import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from fork_checker import can_fork

# PASS (write/admin clearly can fork; none/missing clearly cannot)

def test_write_can_fork():
    assert can_fork({'permission': 'write'}, {}) == True

def test_admin_can_fork():
    assert can_fork({'permission': 'admin'}, {}) == True

def test_no_permission():
    assert can_fork({'permission': 'none'}, {}) == False

def test_missing_permission():
    assert can_fork({}, {}) == False

# FAIL (read permission — bug denies, fix allows)

def test_read_can_fork():
    assert can_fork({'permission': 'read'}, {}) == True  # bug: False

def test_read_with_id():
    assert can_fork({'id': 5, 'permission': 'read'}, {}) == True  # bug: False

def test_read_with_username():
    assert can_fork({'username': 'bob', 'permission': 'read'}, {}) == True  # bug: False
