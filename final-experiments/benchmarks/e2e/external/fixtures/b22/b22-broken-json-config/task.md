# Task: Recover a Corrupted JSON Config File

## Objective

The application in `app/` has a corrupted `config.json` that was truncated during a write operation. A valid backup `config.json.bak` exists. Recover the configuration so the application can start.

## Requirements

1. `app/config.json` must be valid JSON (parseable by `python3 -m json.tool`).
2. The restored config must contain all required keys: `host`, `port`, `database`, `debug`.
3. The values must match the backup file's values.
4. The application must start successfully (`python3 app/main.py` exits 0).

## Current State

- `app/config.json` was truncated mid-write. It is missing closing braces and has incomplete data.
- `app/config.json.bak` contains the last known good configuration.
- `app/main.py` loads `config.json` at startup and will crash if it is invalid.

## Files

- `app/` — the application directory with corrupted config and backup
