# Task: Extract Class to Separate Module

## Objective

Extract the `EmailService` class from the monolithic `app.py` into its own
module `email_service.py`, and update all imports.

## Files

- `app.py` — monolithic file containing multiple classes including EmailService
- `test_app.py` — tests for all functionality

## Requirements

- Create `email_service.py` containing the `EmailService` class
- Remove `EmailService` from `app.py`
- Update imports in `app.py` to use the new module
- Update imports in `test_app.py` to use the new module
- No duplicate code — the class should exist in exactly one place
- All tests must pass
