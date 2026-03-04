"""Hidden tests for cc-002-lru-cache."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solution import LRUCache


class TestLRUCache:
    """Test suite for the LRUCache class."""

    def test_basic_operations(self):
        cache = LRUCache(2)
        cache.put(1, 1)
        cache.put(2, 2)
        assert cache.get(1) == 1
        cache.put(3, 3)  # evicts key 2
        assert cache.get(2) == -1
        cache.put(4, 4)  # evicts key 1
        assert cache.get(1) == -1
        assert cache.get(3) == 3
        assert cache.get(4) == 4

    def test_get_missing_key(self):
        cache = LRUCache(2)
        assert cache.get(1) == -1

    def test_update_existing_key(self):
        cache = LRUCache(2)
        cache.put(1, 10)
        cache.put(1, 20)
        assert cache.get(1) == 20

    def test_capacity_one(self):
        cache = LRUCache(1)
        cache.put(1, 1)
        assert cache.get(1) == 1
        cache.put(2, 2)  # evicts key 1
        assert cache.get(1) == -1
        assert cache.get(2) == 2

    def test_get_refreshes_usage(self):
        cache = LRUCache(2)
        cache.put(1, 1)
        cache.put(2, 2)
        cache.get(1)  # refreshes key 1
        cache.put(3, 3)  # should evict key 2 (LRU), not key 1
        assert cache.get(1) == 1
        assert cache.get(2) == -1
        assert cache.get(3) == 3

    def test_put_refreshes_usage(self):
        cache = LRUCache(2)
        cache.put(1, 1)
        cache.put(2, 2)
        cache.put(1, 10)  # update key 1 — refreshes it
        cache.put(3, 3)  # should evict key 2
        assert cache.get(1) == 10
        assert cache.get(2) == -1
        assert cache.get(3) == 3

    def test_eviction_order(self):
        cache = LRUCache(3)
        cache.put(1, 1)
        cache.put(2, 2)
        cache.put(3, 3)
        cache.get(1)  # refresh 1
        cache.get(2)  # refresh 2
        cache.put(4, 4)  # evicts 3 (LRU)
        assert cache.get(3) == -1
        assert cache.get(1) == 1
        assert cache.get(2) == 2
        assert cache.get(4) == 4

    def test_many_operations(self):
        cache = LRUCache(2)
        for i in range(100):
            cache.put(i, i * 10)
        # Only the last 2 should remain
        assert cache.get(98) == 980
        assert cache.get(99) == 990
        assert cache.get(97) == -1

    def test_zero_value(self):
        cache = LRUCache(2)
        cache.put(1, 0)
        assert cache.get(1) == 0
