# Task: Handle Missing Configuration File Gracefully

## Objective

The application `app.py` crashes with an unhandled `FileNotFoundError` when `config.json` is missing. Add graceful error handling so the app creates a default config file if it doesn't exist.

## Requirements

1. When `config.json` is missing, the app must NOT crash.
2. If `config.json` is missing, create it with sensible defaults (at minimum: `{"debug": false, "port": 8080}`).
3. The app must still work correctly when `config.json` exists.
4. All tests in `test_app.py` must pass.

## Current State

- `app.py` — calls `open("config.json")` without any error handling. Crashes immediately.
- `config.json` — does NOT exist (deleted during setup).
- `test_app.py` — tests for both missing-file and existing-file scenarios.

## Files

- `app.py` — add error handling for missing config
- `test_app.py` — test file (do not modify)
