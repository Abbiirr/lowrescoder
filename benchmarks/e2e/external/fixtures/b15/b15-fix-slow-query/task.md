# Task: Fix Slow User List Query

## User Request

"The user list page is really slow, can you look into it?"

## Context

This is a Python application using SQLite. The user list page loads all users
and their associated department names. The current implementation has a
performance problem that makes it slow with many users.

## Files

- `app.py` — main application with the slow user listing function
- `db.py` — database setup and seeding
- `test_app.py` — tests that verify the user list returns correct data

## Requirements

- Identify and fix the performance issue in the user listing
- The output must remain the same (same data, same format)
- All existing tests must continue to pass
