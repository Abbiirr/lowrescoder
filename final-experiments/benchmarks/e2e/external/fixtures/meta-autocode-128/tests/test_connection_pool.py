import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from connection_pool import add_connection, get_connection, clear_pool

def setup_function():
    clear_pool()

# PASS with bug (healthy connection returned correctly by coincidence)

def test_empty_pool_returns_none():
    assert get_connection() is None

def test_healthy_connection_returned():
    conn = {'id': 1, 'healthy': True}
    add_connection(conn)
    result = get_connection()
    assert result == conn

def test_pool_empty_after_get():
    add_connection({'id': 1, 'healthy': True})
    get_connection()
    assert get_connection() is None

def test_first_connection_taken():
    conn1 = {'id': 1, 'healthy': True}
    conn2 = {'id': 2, 'healthy': True}
    add_connection(conn1)
    add_connection(conn2)
    result = get_connection()
    assert result is not None

# FAIL with bug (unhealthy connections should be skipped)

def test_unhealthy_connection_skipped():
    bad = {'id': 1, 'healthy': False}
    good = {'id': 2, 'healthy': True}
    add_connection(bad)
    add_connection(good)
    result = get_connection()
    assert result == good  # bug: returns bad

def test_only_unhealthy_returns_none():
    add_connection({'id': 1, 'healthy': False})
    assert get_connection() is None  # bug: returns unhealthy conn

def test_skips_multiple_unhealthy():
    add_connection({'id': 1, 'healthy': False})
    add_connection({'id': 2, 'healthy': False})
    add_connection({'id': 3, 'healthy': True})
    result = get_connection()
    assert result['id'] == 3  # bug: returns id=1
