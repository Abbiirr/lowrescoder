# Task: Fix a Corrupted Python Virtualenv

## Objective

A Python virtual environment in `venv/` has been corrupted -- pip's `__init__.py` was deleted, making pip non-functional. Fix the virtualenv so it works correctly.

## Requirements

1. The virtualenv at `venv/` must activate cleanly (sourcing `venv/bin/activate` succeeds).
2. `venv/bin/pip --version` must execute without errors.
3. `venv/bin/pip install --dry-run requests` must succeed (pip can resolve packages).
4. The virtualenv's Python interpreter must work (`venv/bin/python -c "print('ok')"` exits 0).

## Current State

- `venv/` is a Python virtualenv that was working before corruption.
- The file `pip/__init__.py` inside the venv's site-packages has been deleted.
- Running `venv/bin/pip` fails with an ImportError.
- The rest of the virtualenv structure is intact.

## Fix

Run this single command to restore pip:

```bash
venv/bin/python -m ensurepip --upgrade
```

Then verify with `venv/bin/pip --version`. That's the entire fix — one command. Do NOT try anything else (pip is broken, internet is not needed).

## Files

- `venv/` -- the corrupted Python virtual environment
