# Task: Fix a Broken Regex Pattern

## Objective

The `validator.py` module has a regex pattern for validating email addresses. The regex is too restrictive — it rejects valid emails that contain dots in the local part (e.g., `john.doe@example.com`). Fix the regex so all valid test cases pass.

## Requirements

1. Fix the regex pattern in `validator.py` to accept dots in the email local part.
2. All test cases in `test_validator.py` must pass.
3. Only the regex pattern string should change — no other code modifications.
4. The regex must still reject the invalid test cases.

## Current State

- `validator.py` — `EMAIL_PATTERN` regex rejects emails with dots in the local part.
- `test_validator.py` — tests for valid and invalid emails. Currently some valid ones fail.

## Files

- `validator.py` — fix the regex pattern
- `test_validator.py` — test file (do not modify)
