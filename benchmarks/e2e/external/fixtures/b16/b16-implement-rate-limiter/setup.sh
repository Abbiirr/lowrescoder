#!/usr/bin/env bash
# Setup for b16-implement-rate-limiter
# Creates a spec and test file for a token bucket rate limiter.
set -euo pipefail

# Specification document
cat > spec.md << 'SPEC'
# Token Bucket Rate Limiter Specification

## Overview

Implement a `RateLimiter` class that uses the token bucket algorithm to
control the rate of operations.

## Class: `RateLimiter`

### Constructor

```python
RateLimiter(rate: float, capacity: int)
```

- `rate`: Tokens added per second (refill rate)
- `capacity`: Maximum number of tokens the bucket can hold

The bucket starts full (tokens = capacity).

### Methods

#### `allow() -> bool`

Attempt to consume one token. Returns `True` if a token was available
(request allowed), `False` otherwise (request denied).

Before checking, refill tokens based on elapsed time since last refill:
- `tokens = min(capacity, tokens + elapsed_seconds * rate)`

#### `allow_n(n: int) -> bool`

Attempt to consume `n` tokens at once. Returns `True` if enough tokens
were available, `False` otherwise. If not enough tokens, do NOT consume
any (all-or-nothing).

#### `wait_time() -> float`

Return the number of seconds until the next token will be available.
Returns `0.0` if a token is currently available.

### Properties

#### `available_tokens -> float`

Return the current number of available tokens (after refill calculation).

## Behavior Details

- Time tracking should use `time.monotonic()`
- The bucket must handle burst traffic (consuming up to `capacity` tokens
  at once if available)
- Thread safety is NOT required
- Tokens are floating point internally but `allow()` requires >= 1.0

## Module

The class must be importable as:
```python
from rate_limiter import RateLimiter
```
SPEC

# Test file
cat > test_rate_limiter.py << 'PYTHON'
"""Tests for token bucket rate limiter."""
import time
import pytest
from rate_limiter import RateLimiter


class TestRateLimiterBasic:
    def test_starts_full(self):
        rl = RateLimiter(rate=10.0, capacity=5)
        assert rl.available_tokens == 5

    def test_allow_consumes_token(self):
        rl = RateLimiter(rate=10.0, capacity=5)
        assert rl.allow() is True
        assert rl.available_tokens == 4

    def test_allow_when_empty(self):
        rl = RateLimiter(rate=1.0, capacity=2)
        assert rl.allow() is True
        assert rl.allow() is True
        assert rl.allow() is False

    def test_allow_n_success(self):
        rl = RateLimiter(rate=10.0, capacity=10)
        assert rl.allow_n(5) is True
        assert rl.available_tokens == 5

    def test_allow_n_failure_no_partial(self):
        rl = RateLimiter(rate=10.0, capacity=5)
        assert rl.allow_n(6) is False
        # Tokens should not be consumed on failure
        assert rl.available_tokens == 5

    def test_allow_n_exact(self):
        rl = RateLimiter(rate=10.0, capacity=5)
        assert rl.allow_n(5) is True
        assert rl.available_tokens == 0


class TestRateLimiterRefill:
    def test_refill_over_time(self):
        rl = RateLimiter(rate=100.0, capacity=10)
        # Drain all tokens
        for _ in range(10):
            rl.allow()
        assert rl.available_tokens < 1.0
        # Wait for refill
        time.sleep(0.05)  # 50ms at 100/s = ~5 tokens
        tokens = rl.available_tokens
        assert 3.0 <= tokens <= 7.0  # Allow some timing slack

    def test_refill_capped_at_capacity(self):
        rl = RateLimiter(rate=1000.0, capacity=5)
        time.sleep(0.1)  # Would add 100 tokens, but capped at 5
        assert rl.available_tokens == 5

    def test_wait_time_when_empty(self):
        rl = RateLimiter(rate=10.0, capacity=1)
        rl.allow()
        wt = rl.wait_time()
        assert 0.05 <= wt <= 0.15  # ~0.1 seconds for 1 token at 10/s

    def test_wait_time_when_available(self):
        rl = RateLimiter(rate=10.0, capacity=5)
        assert rl.wait_time() == 0.0


class TestRateLimiterBurst:
    def test_burst_then_steady(self):
        rl = RateLimiter(rate=2.0, capacity=5)
        # Burst: consume all 5 at once
        assert rl.allow_n(5) is True
        assert rl.allow() is False
        # Wait for 1 token to refill
        time.sleep(0.6)
        assert rl.allow() is True

    def test_capacity_limits_burst(self):
        rl = RateLimiter(rate=100.0, capacity=3)
        assert rl.allow_n(3) is True
        assert rl.allow() is False
PYTHON

# Create empty implementation file
cat > rate_limiter.py << 'PYTHON'
"""Token bucket rate limiter.

Implement according to spec.md.
"""

# TODO: Implement RateLimiter class
PYTHON

echo "Setup complete. Rate limiter spec and tests created."
