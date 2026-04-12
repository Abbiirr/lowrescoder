#!/usr/bin/env bash
# Setup for b16-implement-retry-decorator
# Creates a spec and test file for an exponential backoff retry decorator.
set -euo pipefail

# Specification document
cat > spec.md << 'SPEC'
# Exponential Backoff Retry Decorator Specification

## Overview

Implement a `retry` decorator that automatically retries a function on
failure with exponential backoff.

## Function: `retry`

### Signature

```python
def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: callable = None,
):
```

### Parameters

- `max_retries`: Maximum number of retry attempts (not counting the initial call)
- `base_delay`: Initial delay between retries in seconds
- `max_delay`: Maximum delay between retries (cap)
- `exponential_base`: Base for exponential backoff calculation
- `exceptions`: Tuple of exception types to catch and retry on
- `on_retry`: Optional callback called on each retry with signature
  `on_retry(attempt: int, exception: Exception, delay: float)`

### Behavior

1. Call the decorated function
2. If it raises an exception in `exceptions`, wait and retry
3. Delay for attempt `n` (0-indexed): `min(base_delay * exponential_base^n, max_delay)`
4. If `max_retries` is exhausted, re-raise the last exception
5. If the function raises an exception NOT in `exceptions`, do not retry — let it propagate immediately
6. The decorator must preserve the original function's name and docstring (use `functools.wraps`)

### Usage Example

```python
@retry(max_retries=3, base_delay=0.1, exceptions=(ConnectionError, TimeoutError))
def fetch_data(url):
    ...
```

## Module

The decorator must be importable as:
```python
from retry import retry
```
SPEC

# Test file
cat > test_retry.py << 'PYTHON'
"""Tests for exponential backoff retry decorator."""
import time
import pytest
from retry import retry


class TestRetryBasic:
    def test_succeeds_without_retry(self):
        call_count = 0

        @retry(max_retries=3, base_delay=0.01)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert succeed() == "ok"
        assert call_count == 1

    def test_retries_on_failure(self):
        call_count = 0

        @retry(max_retries=3, base_delay=0.01)
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        assert fail_twice() == "ok"
        assert call_count == 3

    def test_exhausts_retries(self):
        @retry(max_retries=2, base_delay=0.01)
        def always_fail():
            raise ValueError("always")

        with pytest.raises(ValueError, match="always"):
            always_fail()

    def test_respects_max_retries(self):
        call_count = 0

        @retry(max_retries=2, base_delay=0.01)
        def track_calls():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        with pytest.raises(ValueError):
            track_calls()
        # 1 initial + 2 retries = 3 total calls
        assert call_count == 3


class TestRetryExceptions:
    def test_only_catches_specified_exceptions(self):
        call_count = 0

        @retry(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
        def raise_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            raise_type_error()
        # Should NOT retry on TypeError
        assert call_count == 1

    def test_catches_multiple_exception_types(self):
        call_count = 0

        @retry(max_retries=5, base_delay=0.01, exceptions=(ValueError, KeyError))
        def alternate_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("v")
            if call_count == 2:
                raise KeyError("k")
            return "ok"

        assert alternate_errors() == "ok"
        assert call_count == 3


class TestRetryBackoff:
    def test_exponential_backoff_timing(self):
        """Verify that delays increase exponentially."""
        delays = []

        def track_delay(attempt, exc, delay):
            delays.append(delay)

        @retry(max_retries=3, base_delay=0.1, exponential_base=2.0, on_retry=track_delay)
        def always_fail():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            always_fail()

        # Delays should be: 0.1, 0.2, 0.4
        assert len(delays) == 3
        assert abs(delays[0] - 0.1) < 0.05
        assert abs(delays[1] - 0.2) < 0.05
        assert abs(delays[2] - 0.4) < 0.1

    def test_max_delay_cap(self):
        delays = []

        def track_delay(attempt, exc, delay):
            delays.append(delay)

        @retry(max_retries=5, base_delay=1.0, max_delay=2.0, on_retry=track_delay)
        def always_fail():
            raise ValueError("fail")

        with pytest.raises(ValueError):
            always_fail()

        # All delays should be <= 2.0
        for d in delays:
            assert d <= 2.0


class TestRetryCallback:
    def test_on_retry_called(self):
        retries = []

        def on_retry_cb(attempt, exc, delay):
            retries.append((attempt, str(exc)))

        @retry(max_retries=2, base_delay=0.01, on_retry=on_retry_cb)
        def fail_then_ok():
            if len(retries) < 2:
                raise ValueError(f"attempt {len(retries)}")
            return "ok"

        assert fail_then_ok() == "ok"
        assert len(retries) == 2


class TestRetryPreserves:
    def test_preserves_function_name(self):
        @retry()
        def my_function():
            """My docstring."""
            pass

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."
PYTHON

# Empty implementation
cat > retry.py << 'PYTHON'
"""Exponential backoff retry decorator.

Implement according to spec.md.
"""

# TODO: Implement retry decorator
PYTHON

echo "Setup complete. Retry decorator spec and tests created."
