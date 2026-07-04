# Task: Build an Email Validation Library

## Objective

Build an email validation library per the specification in `project/spec.md`. The library should validate email format, reject known-invalid patterns, and detect disposable email domains.

## Requirements

1. Implement the `validate_email(email)` function in `project/validator.py`.
2. Return a result dict with `valid` (bool), `reason` (str), and `normalized` (str).
3. Follow all validation rules in `project/spec.md`.
4. All tests in `project/test_validator.py` must pass.

## Files

- `project/spec.md` — validation rules specification
- `project/validator.py` — implement the validator here
- `project/disposable_domains.txt` — list of disposable email domains
- `project/test_validator.py` — test file
