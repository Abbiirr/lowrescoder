# Task: Fix a Broken Makefile

## Objective

The `Makefile` for a Python project has several bugs. Fix them so all targets work.

## Requirements

1. `make build` must create a `dist/` directory with a wheel file.
2. `make test` must run pytest and exit 0.
3. `make clean` must remove dist/, build/, and __pycache__/ directories.
4. `make lint` must run ruff check on the source code.
5. All phony targets must be declared.

## Current Bugs

- Indentation uses spaces instead of tabs (Makefile syntax requires tabs)
- `clean` target uses `rm` without `-rf` flag
- `test` target doesn't depend on install
- Missing `.PHONY` declarations
- `build` target has wrong package name

## Files

- `Makefile` — the broken Makefile
- `src/mylib/` — Python package source
- `tests/` — test files
- `pyproject.toml` — package configuration
