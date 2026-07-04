# Task: Fix Open Redirect in OAuth Callback

## Objective

The Flask app in `app/` has an open redirect vulnerability in its OAuth callback endpoint. The `/callback` route accepts a `redirect_url` parameter and redirects to it without validation, allowing attackers to redirect users to malicious external sites. Fix the vulnerability while keeping internal redirects working.

## Requirements

1. **Redirect URL must be validated** — Only allow redirects to URLs on the same domain or a configured whitelist.
2. **External URLs must be rejected** — Requests with external/malicious redirect URLs should be redirected to a safe default (e.g., `/dashboard`).
3. **Internal redirects still work** — Relative paths like `/profile` or `/settings` must still redirect correctly.
4. **All existing tests must pass** (`python -m pytest test_app.py`).

## Current State

- `app/app.py` — Flask application with `/callback` endpoint that blindly redirects to the `redirect_url` query parameter.
- `app/test_app.py` — Tests for the callback endpoint and other routes.

## Files

- `app/` — the vulnerable Flask application
