# Task: Fix Database Schema Drift

## Objective

The SQLite database schema has drifted from the SQLAlchemy ORM models. The database has extra columns and is missing columns that the models define. Fix the database so its schema matches the models exactly, preserving existing data.

## Requirements

1. The `users` table must match the `User` model exactly (columns, types).
2. The `posts` table must match the `Post` model exactly (columns, types).
3. Existing data in the database must be preserved (no data loss).
4. New columns added to the DB should have sensible defaults for existing rows.
5. The validation script (`validate_models.py`) must pass.

## Current State

- `models.py` — SQLAlchemy ORM models defining the desired schema. This is the source of truth.
- `app.db` — SQLite database with drifted schema:
  - `users` table: missing `email` column, has extra `legacy_role` column not in model.
  - `posts` table: missing `updated_at` column, has extra `view_count` column not in model.
- `validate_models.py` — Script that checks DB schema matches models.

## Important

- The models are correct. Fix the database to match them.
- Do NOT modify `models.py` or `validate_models.py`.
- Preserve all existing row data (names, titles, content, timestamps).

## Files

- `models.py` — ORM models (DO NOT MODIFY)
- `validate_models.py` — Validation script (DO NOT MODIFY)
- `app.db` — Database to fix
