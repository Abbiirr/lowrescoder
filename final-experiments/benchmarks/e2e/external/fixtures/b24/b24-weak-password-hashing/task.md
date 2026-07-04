# Task: Replace Weak Password Hashing with a Secure Algorithm

## Objective

The user authentication module in `app/` uses MD5 to hash passwords, which is cryptographically broken for this purpose. Replace it with a secure password hashing algorithm (bcrypt, argon2, or PBKDF2) while ensuring existing functionality continues to work.

## Requirements

1. **No MD5 or SHA1 for password hashing** — Remove all uses of `hashlib.md5` or `hashlib.sha1` for password storage/verification.
2. **Use a secure algorithm** — Passwords must be hashed with `bcrypt`, `argon2`, or `pbkdf2` (via `hashlib.pbkdf2_hmac` or a dedicated library).
3. **Password verification must work** — The `verify_password` function must correctly verify passwords against the new hashes.
4. **User registration and login still work** — Creating users and authenticating them must function correctly.
5. **All existing tests must pass** (`python -m pytest test_app.py`).

## Current State

- `app/auth.py` — Authentication module using `hashlib.md5` for password hashing. Has `hash_password`, `verify_password`, `create_user`, and `authenticate` functions.
- `app/test_app.py` — Tests for user registration, login, and password verification.

## Files

- `app/` — the authentication module with weak password hashing
