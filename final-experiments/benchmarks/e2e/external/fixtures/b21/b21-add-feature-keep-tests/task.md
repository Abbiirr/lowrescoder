# Task: Add a New Endpoint Without Breaking Existing Tests

## Objective

Add a new `/status` endpoint to the Flask app in `app.py` without breaking the 3 existing test cases.

## Requirements

1. Add a `GET /status` endpoint that returns JSON `{"status": "healthy", "version": "1.1.0"}` with HTTP 200.
2. All 3 existing tests in `test_app.py` must continue to pass without modification.
3. **Add a new test function** in `test_app.py` that tests the `/status` endpoint. The test function name must contain "status" (e.g. `test_status`). This is required — the task is NOT complete without this test.
4. The app must remain importable and runnable.

**Important:** You must edit BOTH `app.py` (add the endpoint) AND `test_app.py` (add the test). Verification will fail if the test is missing.

## Current State

- `app.py` — Flask application with 3 endpoints: `GET /`, `GET /users`, `POST /users`.
- `test_app.py` — 3 passing tests covering each endpoint.
- The app is working correctly; do not change existing behavior.

## Files

- `app.py` — Flask application to modify
- `test_app.py` — Test file (existing tests must still pass)
