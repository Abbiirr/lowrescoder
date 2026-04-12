# Task: Add Input Validation

## User Request

"Users can submit empty forms, please add validation"

## Context

There is a form handler that accepts user registration data. Currently it
accepts any input, including empty strings and missing fields, which creates
bad data in the system.

## Files

- `forms.py` — form handler that processes user registration
- `test_forms.py` — existing tests for form handling

## Requirements

- Required fields (name, email, password) must not be empty
- Email must contain @ and a domain
- Password must be at least 8 characters
- Return clear error messages for each validation failure
- Existing tests must continue to pass
