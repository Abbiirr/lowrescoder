"""In-memory cache with configurable max size.

Bug: the cache grows without bound because there is no eviction logic.
The max_size parameter is accepted but never enforced.
Fix: evict the oldest entry when the cache exceeds max_size.
"""


class Cache:
    """Simple key-value cache with a maximum size.

    Bug: max_size is stored but never used. The internal dict grows
    without limit, causing a memory leak in long-running processes.
    """

    def __init__(self, max_size=100):
        self.max_size = max_size
        self._store = {}
        self._access_order = []  # tracks insertion order

    def get(self, key):
        """Get a value from cache. Returns None if not found."""
        return self._store.get(key)

    def put(self, key, value):
        """Put a value into cache.

        Bug: never evicts old entries when cache exceeds max_size.
        Should remove the oldest entry when len exceeds max_size.
        """
        if key not in self._store:
            self._access_order.append(key)
        self._store[key] = value
        # Bug: missing eviction logic here
        # Should check: while len(self._store) > self.max_size: evict oldest

    def size(self):
        """Return current number of entries in cache."""
        return len(self._store)

    def contains(self, key):
        """Check if key exists in cache."""
        return key in self._store

    def clear(self):
        """Clear all entries."""
        self._store.clear()
        self._access_order.clear()

    def keys(self):
        """Return all keys in cache."""
        return list(self._store.keys())
