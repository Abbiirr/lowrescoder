#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/counter.py << 'PYEOF'
"""Counter module — a simple counter class."""


class Counter:
    """A counter that can be incremented and decremented.

    WARNING: This counter is NOT thread-safe. Concurrent access
    will produce incorrect results.
    """

    def __init__(self, initial=0):
        self._count = initial

    def increment(self, amount=1):
        """Increment the counter by amount.

        Args:
            amount: Amount to increment by (default 1).
        """
        # BUG: No locking — this is a read-modify-write race condition.
        # Under concurrent access, some increments are lost.
        current = self._count
        self._count = current + amount

    def decrement(self, amount=1):
        """Decrement the counter by amount.

        Args:
            amount: Amount to decrement by (default 1).
        """
        current = self._count
        self._count = current - amount

    @property
    def value(self):
        """Return the current count."""
        return self._count

    def reset(self):
        """Reset the counter to zero."""
        self._count = 0
PYEOF

cat > project/test_counter.py << 'PYEOF'
"""Tests for the counter module."""
import unittest
import threading
from counter import Counter


class TestCounterBasic(unittest.TestCase):
    """Basic single-threaded tests."""

    def test_initial_value(self):
        c = Counter()
        self.assertEqual(c.value, 0)

    def test_initial_custom(self):
        c = Counter(initial=42)
        self.assertEqual(c.value, 42)

    def test_increment(self):
        c = Counter()
        c.increment()
        self.assertEqual(c.value, 1)

    def test_decrement(self):
        c = Counter(initial=10)
        c.decrement()
        self.assertEqual(c.value, 9)

    def test_increment_by_amount(self):
        c = Counter()
        c.increment(5)
        self.assertEqual(c.value, 5)

    def test_reset(self):
        c = Counter(initial=100)
        c.reset()
        self.assertEqual(c.value, 0)


class TestCounterConcurrent(unittest.TestCase):
    """Concurrent tests — these expose the race condition."""

    def test_concurrent_increment(self):
        """100 threads each increment 1000 times. Expected: 100000."""
        c = Counter()
        num_threads = 100
        increments_per_thread = 1000

        def worker():
            for _ in range(increments_per_thread):
                c.increment()

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = num_threads * increments_per_thread
        self.assertEqual(c.value, expected,
                         f"Expected {expected}, got {c.value} — race condition!")

    def test_concurrent_mixed(self):
        """50 threads increment, 50 decrement, each 1000 times. Expected: 0."""
        c = Counter()
        ops_per_thread = 1000

        def incrementer():
            for _ in range(ops_per_thread):
                c.increment()

        def decrementer():
            for _ in range(ops_per_thread):
                c.decrement()

        threads = []
        for _ in range(50):
            threads.append(threading.Thread(target=incrementer))
            threads.append(threading.Thread(target=decrementer))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(c.value, 0,
                         f"Expected 0, got {c.value} — race condition!")


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. counter.py has no locking — concurrent access produces wrong results."
