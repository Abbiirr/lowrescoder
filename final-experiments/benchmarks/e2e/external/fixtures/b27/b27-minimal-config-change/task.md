# Task: Fix a Wrong Port in Configuration

## Objective

The application in this directory connects to a backend service, but the config file has the wrong port number. The service runs on port `8080`, but `config.yaml` points to port `9090`. Fix the config so the connection test passes.

## Requirements

1. Change the port in `config.yaml` from `9090` to `8080`.
2. The test in `test_app.py` must pass.
3. Only `config.yaml` should be modified — no code changes.
4. The diff should be minimal (one value changed).

## Current State

- `config.yaml` — has `port: 9090` (wrong).
- `app.py` — reads config and connects to the specified host:port.
- `test_app.py` — mocks the service on port 8080 and verifies the app connects correctly.

## Files

- `config.yaml` — configuration file to fix
- `app.py` — application code (do not modify)
- `test_app.py` — test file (do not modify)
