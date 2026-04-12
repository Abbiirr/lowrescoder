# Task: Complete a Half-Applied Database Migration

## Objective

A SQLite database migration was interrupted midway. Some tables were created, others were not. Complete the migration so all tables exist with the correct schemas.

## Requirements

1. All 4 tables must exist: `users`, `posts`, `comments`, `tags`.
2. Each table must have the correct columns as defined in `migration.sql`.
3. There must be no duplicate tables.
4. The `migration_log` table must have an entry recording that the migration was completed.
5. The existing data in already-created tables (`users`, `posts`) must not be lost.

## Current State

- `app.db` is a SQLite database with 2 of 4 tables already created (`users` and `posts`).
- `users` has one seed row (admin user). This data must survive the fix.
- `posts` has one seed row. This data must survive the fix.
- `migration.sql` contains the full migration script that defines all 4 tables.
- Tables `comments` and `tags` do not exist yet.
- The `migration_log` table exists but has no entry for this migration.

## Files

- `app.db` — the SQLite database in a partially migrated state
- `migration.sql` — the full migration script
