# LRU Cache

## Problem

Design a data structure that follows the constraints of a Least Recently Used (LRU) cache.

Implement the `LRUCache` class:

- `LRUCache(capacity: int)` — Initialize the LRU cache with positive size `capacity`.
- `get(key: int) -> int` — Return the value of the `key` if it exists, otherwise return `-1`.
- `put(key: int, value: int) -> None` — Update the value of the `key` if it exists. Otherwise, add the key-value pair to the cache. If the number of keys exceeds the `capacity`, evict the least recently used key.

The functions `get` and `put` must each run in O(1) average time complexity.

## Class Signature

```python
class LRUCache:
    def __init__(self, capacity: int):
        ...

    def get(self, key: int) -> int:
        ...

    def put(self, key: int, value: int) -> None:
        ...
```

## Constraints

- `1 <= capacity <= 3000`
- `0 <= key <= 10^4`
- `0 <= value <= 10^5`
- At most `2 * 10^5` calls will be made to `get` and `put`.

## Examples

**Example 1:**
```
cache = LRUCache(2)
cache.put(1, 1)
cache.put(2, 2)
cache.get(1)       # returns 1
cache.put(3, 3)    # evicts key 2
cache.get(2)       # returns -1 (not found)
cache.get(3)       # returns 3
cache.put(4, 4)    # evicts key 1
cache.get(1)       # returns -1 (not found)
cache.get(3)       # returns 3
cache.get(4)       # returns 4
```
