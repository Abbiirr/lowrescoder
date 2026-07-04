# Task: Fix a Broken Shell Data Pipeline

## Objective

The `pipeline.sh` script reads CSV data, filters rows, sorts them, and outputs JSON. It has several bugs that prevent it from producing correct output. Fix all bugs.

## Requirements

1. `pipeline.sh` must exit 0 when run successfully.
2. The script must read `data.csv`, filter rows where the `status` column is "active", sort by the `name` column alphabetically, and output valid JSON to `output.json`.
3. The JSON output must be an array of objects with `name`, `email`, and `status` fields.
4. The pipeline must not produce any shellcheck warnings (SC-level errors).

## Current Bugs

- `grep` uses `-P` (Perl regex) flag unnecessarily and has a wrong pattern that misses valid rows
- `sort` step is missing entirely — output is unsorted
- `awk` field separator is wrong (uses space instead of comma) causing broken JSON output

## Files

- `pipeline.sh` — the broken data processing pipeline
- `data.csv` — input CSV data
