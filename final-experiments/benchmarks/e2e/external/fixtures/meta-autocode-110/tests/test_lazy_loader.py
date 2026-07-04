import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from lazy_loader import get_or_load, _cache

def make_counter():
    count = [0]
    def loader():
        count[0] += 1
        return count[0]
    return loader, count

# PASS with bug (first call behavior same)

def test_returns_value():
    _cache.clear()
    assert get_or_load('a', lambda: 42) == 42

def test_different_keys():
    _cache.clear()
    get_or_load('x', lambda: 1)
    assert get_or_load('y', lambda: 2) == 2

def test_none_value_returned():
    _cache.clear()
    assert get_or_load('n', lambda: None) is None

def test_string_value():
    _cache.clear()
    assert get_or_load('s', lambda: 'hello') == 'hello'

# FAIL with bug (loader called every time instead of once)

def test_loader_called_only_once():
    _cache.clear()
    loader, count = make_counter()
    get_or_load('k1', loader)
    get_or_load('k1', loader)
    assert count[0] == 1  # bug: 2 (loader called on both calls)

def test_cached_value_returned():
    _cache.clear()
    loader, count = make_counter()
    get_or_load('k2', loader)
    result = get_or_load('k2', loader)
    assert result == 1  # bug: 2 (second call to loader returns 2)

def test_loader_not_called_after_cache():
    _cache.clear()
    calls = [0]
    def loader():
        calls[0] += 1
        return 'data'
    get_or_load('k3', loader)
    get_or_load('k3', loader)
    get_or_load('k3', loader)
    assert calls[0] == 1  # bug: 3
