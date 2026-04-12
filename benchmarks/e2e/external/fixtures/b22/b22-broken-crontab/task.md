# Task: Fix Broken Crontab Entries

## Objective

A crontab file has 5 scheduled job entries, but 3 of them have syntax errors. Fix all entries so they are valid cron syntax and reference existing scripts.

## Requirements

1. The file `crontab.txt` must contain exactly 5 cron entries (non-comment, non-blank lines).
2. All 5 entries must have valid cron time specifications (5 fields: minute, hour, day-of-month, month, day-of-week).
3. All commands must reference scripts that exist in the `scripts/` directory.
4. The corrected entries must preserve the original intent (which script to run and approximate schedule).
5. The file must be parseable by `crontab crontab.txt` (valid cron format overall).

## Current State

- `crontab.txt` has 5 entries. Three have errors:
  - Entry for `backup.sh`: has 6 time fields instead of 5.
  - Entry for `cleanup.sh`: minute field is `65` (invalid, max is 59).
  - Entry for `report.sh`: missing the command entirely (only has time fields).
- `scripts/` directory contains all 5 scripts that should be referenced.
- Two entries (`health_check.sh` and `rotate_logs.sh`) are correct.

## Files

- `crontab.txt` -- the broken crontab file
- `scripts/` -- directory with the referenced scripts
