#!/usr/bin/env bash
# Setup for b16-implement-cache-layer
# Creates a spec and test file for a TTL-based LRU cache.
set -euo pipefail

# Specification document
cat > spec.md << 'SPEC'
# TTL-Based LRU Cache Specification

## Overview

Implement an `LRUCache` class that combines Least Recently Used eviction
with Time-To-Live expiration.

## Class: `LRUCache`

### Constructor

```python
LRUCache(capacity: int, default_ttl: float = 60.0)
```

- `capacity`: Maximum number of items the cache can hold
- `default_ttl`: Default time-to-live in seconds for cached items

### Methods

#### `get(key: str) -> any`

Retrieve value for `key`. Returns `None` if key is not found or has expired.
Accessing a key marks it as recently used. Expired entries should be removed
on access.

#### `put(key: str, value: any, ttl: float = None) -> None`

Store `value` under `key`. If `ttl` is provided, use it; otherwise use
`default_ttl`. If the cache is at capacity, evict the least recently used
non-expired item. If all items are expired, evict the oldest expired item.

#### `delete(key: str) -> bool`

Remove `key` from the cache. Returns `True` if the key existed, `False`
otherwise.

#### `clear() -> None`

Remove all items from the cache.

#### `keys() -> list[str]`

Return a list of all non-expired keys, ordered from most recently used to
least recently used.

### Properties

#### `size -> int`

Number of non-expired items currently in the cache.

## Behavior Details

- Use `time.monotonic()` for time tracking
- Items with TTL <= 0.0 should be treated as "no expiration"
- The cache must handle string keys only
- Values can be of any type

## Module

The class must be importable as:
```python
from cache import LRUCache
```
SPEC

# Test file
cat > test_cache.py << 'PYTHON'
"""Tests for TTL-based LRU cache."""
import time
import pytest
from cache import LRUCache


class TestCacheBasic:
    def test_put_and_get(self):
        c = LRUCache(capacity=10)
        c.put("a", 1)
        assert c.get("a") == 1

    def test_get_missing_key(self):
        c = LRUCache(capacity=10)
        assert c.get("missing") is None

    def test_overwrite_key(self):
        c = LRUCache(capacity=10)
        c.put("a", 1)
        c.put("a", 2)
        assert c.get("a") == 2

    def test_delete_existing(self):
        c = LRUCache(capacity=10)
        c.put("a", 1)
        assert c.delete("a") is True
        assert c.get("a") is None

    def test_delete_missing(self):
        c = LRUCache(capacity=10)
        assert c.delete("missing") is False

    def test_clear(self):
        c = LRUCache(capacity=10)
        c.put("a", 1)
        c.put("b", 2)
        c.clear()
        assert c.size == 0
        assert c.get("a") is None

    def test_size(self):
        c = LRUCache(capacity=10)
        assert c.size == 0
        c.put("a", 1)
        assert c.size == 1
        c.put("b", 2)
        assert c.size == 2


class TestCacheLRU:
    def test_evicts_lru_at_capacity(self):
        c = LRUCache(capacity=3, default_ttl=0)  # No expiration
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        c.put("d", 4)  # Should evict "a"
        assert c.get("a") is None
        assert c.get("b") == 2

    def test_access_updates_lru_order(self):
        c = LRUCache(capacity=3, default_ttl=0)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        c.get("a")  # "a" is now most recent
        c.put("d", 4)  # Should evict "b" (least recent)
        assert c.get("a") == 1
        assert c.get("b") is None

    def test_keys_ordered_mru_to_lru(self):
        c = LRUCache(capacity=5, default_ttl=0)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        c.get("a")  # a is now most recent
        keys = c.keys()
        assert keys[0] == "a"
        assert keys[-1] == "b"


class TestCacheTTL:
    def test_expired_item_returns_none(self):
        c = LRUCache(capacity=10, default_ttl=0.1)
        c.put("a", 1)
        time.sleep(0.15)
        assert c.get("a") is None

    def test_non_expired_item_returns_value(self):
        c = LRUCache(capacity=10, default_ttl=1.0)
        c.put("a", 1)
        assert c.get("a") == 1

    def test_custom_ttl_per_item(self):
        c = LRUCache(capacity=10, default_ttl=10.0)
        c.put("short", 1, ttl=0.1)
        c.put("long", 2, ttl=10.0)
        time.sleep(0.15)
        assert c.get("short") is None
        assert c.get("long") == 2

    def test_no_expiration_with_zero_ttl(self):
        c = LRUCache(capacity=10, default_ttl=0)
        c.put("a", 1)
        # Zero TTL means no expiration
        assert c.get("a") == 1

    def test_size_excludes_expired(self):
        c = LRUCache(capacity=10, default_ttl=0.1)
        c.put("a", 1)
        c.put("b", 2, ttl=10.0)
        time.sleep(0.15)
        assert c.size == 1  # Only "b" is alive

    def test_keys_excludes_expired(self):
        c = LRUCache(capacity=10, default_ttl=0.1)
        c.put("a", 1)
        c.put("b", 2, ttl=10.0)
        time.sleep(0.15)
        keys = c.keys()
        assert "a" not in keys
        assert "b" in keys
PYTHON

# Empty implementation
cat > cache.py << 'PYTHON'
"""TTL-based LRU cache.

Implement according to spec.md.
"""

# TODO: Implement LRUCache class
PYTHON

echo "Setup complete. LRU cache spec and tests created."
