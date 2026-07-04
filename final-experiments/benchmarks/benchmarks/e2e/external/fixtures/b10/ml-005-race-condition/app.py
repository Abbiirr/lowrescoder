"""Thread-safe counter implementation."""
import threading


class Counter:
    """A counter that should be safe for concurrent access.

    Bug: increment/decrement are not protected by a lock,
    causing lost updates under concurrent access.
    """

    def __init__(self):
        self.value = 0
        # Bug: lock exists but is not used in increment/decrement
        self.lock = threading.Lock()

    def increment(self):
        """Increment counter by 1. Bug: not thread-safe."""
        # Bug: no lock protection. Read-modify-write is not atomic.
        temp = self.value
        self.value = temp + 1

    def decrement(self):
        """Decrement counter by 1. Bug: not thread-safe."""
        temp = self.value
        self.value = temp - 1

    def get(self):
        """Get current counter value."""
        return self.value

    def reset(self):
        """Reset counter to zero."""
        self.value = 0


def run_increments(counter, n):
    """Increment counter n times."""
    for _ in range(n):
        counter.increment()


def run_decrements(counter, n):
    """Decrement counter n times."""
    for _ in range(n):
        counter.decrement()
