# Task: Make a Database Migration Idempotent

## Objective

The database migration script in `project/migrate.py` fails when run a second time because it tries to create tables and insert data that already exist. Fix it so it can be run multiple times safely (idempotent).

## Requirements

1. Running `migrate.py` once creates the schema and inserts seed data.
2. Running `migrate.py` again must not error, must not duplicate data, and must preserve existing data.
3. Schema must be correct after any number of runs.
4. The migration must be safe when called repeatedly in the same Python process; do not leave SQLite connections locked between runs.
5. All tests in `project/test_migrate.py` must pass.

## Implementation Notes

- Ensure every migration run releases its SQLite connection cleanly, even if something goes wrong.
- If needed, it is acceptable to use a SQLite connection timeout or `PRAGMA busy_timeout` to avoid transient `database is locked` failures during repeated writes.
- Solve this in `project/migrate.py`. Do not delete, recreate, or hand-edit `project/app.db`; the verifier reruns against the existing database state.

## Files

- `project/migrate.py` — the migration script (needs to be made idempotent)
- `project/app.db` — SQLite database (already has one migration run)
- `project/test_migrate.py` — test file
