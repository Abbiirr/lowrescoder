# Task: Fix Broken Symlinks After Directory Move

## Objective

A project in `project/` has broken symbolic links after a directory restructuring. Find and fix all broken symlinks so they point to the correct targets.

## Requirements

1. All symbolic links in `project/config/` must resolve (no broken symlinks).
2. Each symlink must point to the correct corresponding file in `project/vendor/lib/`.
3. The actual library files in `project/vendor/lib/` must remain unchanged.
4. Reading each symlink (e.g., `cat project/config/db.conf`) must return the correct file content.
5. No broken symlinks anywhere in `project/`.
6. Do NOT replace symlinks with copies of the files — they must remain symbolic links.

## Current State

- The project originally had library files in `project/lib/` and config symlinks in `project/config/` pointing to `../lib/<file>`.
- The `lib/` directory was moved to `vendor/lib/`, breaking all symlinks in `config/`.
- There are 5 broken symlinks in `config/`: `db.conf`, `cache.conf`, `auth.conf`, `logging.conf`, `routes.conf`.
- There is also a `project/bin/run` symlink pointing at a script in the old `lib/` location.
- The files they should point to exist under `project/vendor/lib/`.

## Files

- `project/` — the project directory with broken symlinks
