# Task: Add Timeout and Retry to HTTP Request

## Objective

The function `fetch_data` in `client.py` calls `requests.get()` without a timeout, which can hang indefinitely. Add a timeout parameter and retry logic so the function is resilient to transient network failures.

## Requirements

1. Add a `timeout` parameter to the `requests.get()` call (e.g., 5 seconds).
2. Add retry logic: retry up to 3 times on timeout or connection errors.
3. Raise a clear error after all retries are exhausted.
4. All tests in `test_client.py` must pass.

## Current State

- `client.py` — `fetch_data(url)` calls `requests.get(url)` with no timeout or retry.
- `test_client.py` — tests that mock timeouts and verify retry behavior.

## Files

- `client.py` — add timeout and retry logic
- `test_client.py` — test file (do not modify)
