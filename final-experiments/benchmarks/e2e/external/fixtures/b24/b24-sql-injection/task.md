# Task: Fix SQL Injection in Login Endpoint

## Objective

The Flask app in `app/` has a SQL injection vulnerability in its login endpoint. Fix the vulnerability while keeping the login functionality working.

## Requirements

1. The login endpoint must use **parameterized queries** (placeholders) instead of string formatting to construct SQL.
2. No f-strings, `%` formatting, or `.format()` calls may be used to build SQL query strings.
3. The login functionality must still work correctly — valid credentials succeed, invalid credentials fail.
4. All existing tests must continue to pass (`python -m pytest test_app.py`).

## Current State

- `app/app.py` — Flask application with a `/login` POST endpoint. The SQL query is built using an f-string, making it vulnerable to SQL injection.
- `app/test_app.py` — Tests for the login endpoint covering valid login, invalid password, and unknown user.
- `app/init_db.py` — Database initialization script that creates the users table and seeds a test user.

## Files

- `app/` — the vulnerable Flask application
