# Task: Rotate Server Logs

## Objective

The server logs in `logs/` need manual rotation. Compress current logs, truncate active log files, and maintain a rotation history.

## Requirements

1. **Rotate `app.log`:**
   - Compress the current contents to `app.log.1.gz` (valid gzip file).
   - Truncate `app.log` in place so it exists but has fewer than 100 lines (ideally 0).
   - If `app.log.1.gz` already existed, shift it to `app.log.2.gz` first. Shift `app.log.2.gz` to `app.log.3.gz`. Drop anything beyond `.3.gz`.

2. **Rotate `access.log`:**
   - Compress the current contents to `access.log.1.gz` (valid gzip file).
   - Truncate `access.log` in place so it exists but has fewer than 100 lines (ideally 0).
   - Shift existing rotations the same way as `app.log`.

3. **Preserve existing rotations:**
   - `app.log.1.gz` (pre-existing) must be shifted to `app.log.2.gz`.
   - `access.log.1.gz` (pre-existing) must be shifted to `access.log.2.gz`.
   - Keep at most 3 numbered rotations (`.1.gz`, `.2.gz`, `.3.gz`).

4. **File integrity:**
   - All `.gz` files must be valid gzip (pass `gzip -t`).
   - The newly created `.1.gz` files must contain the data that was in the current log.
   - The shifted `.2.gz` files must contain the data from the old `.1.gz`.
   - `app.log` and `access.log` must still exist after rotation (not deleted).

## Current State

- `logs/app.log` — 5000 lines of application log entries.
- `logs/access.log` — 3000 lines of HTTP access log entries.
- `logs/app.log.1.gz` — a previous rotation of app.log (contains older entries).
- `logs/access.log.1.gz` — a previous rotation of access.log (contains older entries).

## Files

- `logs/` — the directory containing all log files
