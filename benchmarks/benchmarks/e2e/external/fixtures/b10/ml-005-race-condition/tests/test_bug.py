"""Tests for race condition bug in threaded counter."""
import sys
import os
import threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import Counter, run_increments, run_decrements


def test_single_thread_increment():
    """Single-threaded increment should work correctly."""
    c = Counter()
    for _ in range(1000):
        c.increment()
    assert c.get() == 1000


def test_single_thread_decrement():
    """Single-threaded decrement should work correctly."""
    c = Counter()
    c.value = 1000
    for _ in range(1000):
        c.decrement()
    assert c.get() == 0


def test_concurrent_increments():
    """Multiple threads incrementing should produce exact count.

    Bug: without lock protection, concurrent read-modify-write causes
    lost updates, so the final value will be less than expected.
    """
    c = Counter()
    num_threads = 8
    increments_per_thread = 10000
    expected = num_threads * increments_per_thread

    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=run_increments, args=(c, increments_per_thread))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert c.get() == expected, (
        f"Expected {expected}, got {c.get()} — race condition detected"
    )


def test_concurrent_increment_decrement():
    """Equal increments and decrements should cancel to zero.

    Bug: without lock, final value drifts from zero.
    """
    c = Counter()
    num_threads = 4
    ops_per_thread = 10000

    threads = []
    for _ in range(num_threads):
        threads.append(threading.Thread(target=run_increments, args=(c, ops_per_thread)))
        threads.append(threading.Thread(target=run_decrements, args=(c, ops_per_thread)))

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert c.get() == 0, (
        f"Expected 0 (balanced inc/dec), got {c.get()} — race condition detected"
    )


def test_reset_and_reuse():
    """Counter should work correctly after reset."""
    c = Counter()
    c.increment()
    c.increment()
    assert c.get() == 2
    c.reset()
    assert c.get() == 0
    c.increment()
    assert c.get() == 1
