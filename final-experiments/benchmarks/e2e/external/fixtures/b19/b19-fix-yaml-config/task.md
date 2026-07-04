# Task: Fix a Broken YAML Configuration

## Objective

The `config.yaml` file for a Python application has several errors that prevent the app from loading its configuration. Fix all errors in the YAML file.

## Requirements

1. `config.yaml` must be valid YAML (parseable without errors).
2. All required keys must be present: `server.host`, `server.port`, `database.host`, `database.port`, `database.name`, `logging.level`, `logging.file`.
3. `server.port` and `database.port` must be integers, not strings.
4. `logging.level` must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL.
5. The application (`app.py`) must load the config successfully and start without errors.

## Current Bugs

- Indentation error: `database` section has inconsistent indentation causing parse failure
- `server.port` is a quoted string `"8080"` instead of an integer `8080`
- `database.name` key is missing entirely

## Files

- `config.yaml` — the broken configuration file
- `app.py` — Python application that loads and validates the config
