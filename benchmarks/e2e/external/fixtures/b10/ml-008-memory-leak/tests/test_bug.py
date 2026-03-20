"""Tests for memory leak bug in cache implementation."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import Cache


def test_basic_put_get():
    """Basic put/get should work."""
    c = Cache(max_size=10)
    c.put("a", 1)
    assert c.get("a") == 1


def test_overwrite_value():
    """Putting the same key should overwrite."""
    c = Cache(max_size=10)
    c.put("a", 1)
    c.put("a", 2)
    assert c.get("a") == 2
    assert c.size() == 1


def test_get_missing_returns_none():
    """Getting a missing key should return None."""
    c = Cache(max_size=10)
    assert c.get("missing") is None


def test_cache_respects_max_size():
    """Cache should not grow beyond max_size.

    This is the core bug: the cache never evicts, so it grows
    beyond max_size indefinitely.
    """
    c = Cache(max_size=5)
    for i in range(20):
        c.put(f"key-{i}", i)

    assert c.size() <= 5, (
        f"Cache size is {c.size()}, should be <= 5 (max_size). "
        "Cache is not evicting old entries — memory leak!"
    )


def test_eviction_removes_oldest():
    """When cache is full, oldest entry should be evicted."""
    c = Cache(max_size=3)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    # Cache is full (3/3), adding "d" should evict "a"
    c.put("d", 4)

    assert c.size() <= 3, f"Cache should have at most 3 entries, has {c.size()}"
    assert c.get("a") is None, "Oldest entry 'a' should have been evicted"
    assert c.get("d") == 4, "Newest entry 'd' should be present"


def test_large_number_of_insertions():
    """Inserting many items should not cause unbounded growth."""
    c = Cache(max_size=10)
    for i in range(10000):
        c.put(f"item-{i}", i)

    assert c.size() <= 10, (
        f"After 10000 insertions, cache has {c.size()} entries "
        f"but max_size is 10 — memory leak detected"
    )


def test_contains_after_eviction():
    """Evicted keys should not be found by contains()."""
    c = Cache(max_size=2)
    c.put("x", 1)
    c.put("y", 2)
    c.put("z", 3)  # should evict "x"

    assert c.contains("z") is True
    assert c.contains("x") is False, "Evicted key 'x' should not be in cache"


def test_clear():
    """Clear should empty the cache."""
    c = Cache(max_size=10)
    c.put("a", 1)
    c.put("b", 2)
    c.clear()
    assert c.size() == 0
    assert c.get("a") is None
