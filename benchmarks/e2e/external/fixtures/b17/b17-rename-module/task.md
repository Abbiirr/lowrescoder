# Task: Rename Module

## Objective

Rename the `utils.py` module to `helpers.py` and update all imports across
the codebase.

## Files

- `utils.py` — the module to be renamed
- `app.py` — main application (imports from utils)
- `services.py` — service layer (imports from utils)
- `api.py` — API layer (imports from utils)
- `models.py` — data models (imports from utils)
- `test_app.py` — tests (imports from utils)

## Requirements

- Rename `utils.py` to `helpers.py`
- Update all imports in all files that reference `utils`, including `test_app.py`
- No `import utils` or `from utils import` should remain
- All tests must pass after the rename
- No duplicate code — the old `utils.py` should not exist
- It is allowed and expected to edit `test_app.py` so its imports match the renamed module.
