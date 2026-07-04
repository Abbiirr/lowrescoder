# Task: Fix Broken File Permissions

## Objective

The `webapp/` directory has broken file permissions that need to be fixed according to security best practices.

## Requirements

Fix the permissions so that:

1. **Public directory** (`webapp/public/` and everything inside):
   - Directories: `755` (rwxr-xr-x)
   - Files: `644` (rw-r--r--)

2. **Config directory** (`webapp/config/`):
   - Directory: `750` (rwxr-x---)
   - Files: `600` (rw-------)

3. **Logs directory** (`webapp/logs/`):
   - Directory: `750` (rwxr-x---)
   - Files: `640` (rw-r-----)

4. **Scripts directory** (`webapp/scripts/`):
   - Directory: `750` (rwxr-x---)
   - Files: `750` (rwxr-x---)

## Current State

- `webapp/public/` is `000` (completely inaccessible)
- Config files are `777` (world-readable secrets!)
- Logs are `777`/`666` (world-writable)
- Scripts have no execute bit

## Files

- `webapp/` — the web application directory tree to fix
