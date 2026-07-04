# Task: Fix Date Parsing for ISO 8601 Timezone Offsets

## Objective

The date parser in `project/dateparser.py` handles naive dates and UTC ("Z") but crashes on ISO 8601 dates with timezone offsets like "+05:30" or "-08:00". Fix the parser to handle all standard ISO 8601 date formats.

## Requirements

1. Parse naive dates: `2024-01-15`, `2024-01-15T10:30:00`
2. Parse UTC dates: `2024-01-15T10:30:00Z`
3. Parse dates with timezone offsets: `2024-01-15T10:30:00+05:30`, `2024-01-15T10:30:00-08:00`
4. Parse dates with zero offset: `2024-01-15T10:30:00+00:00`
5. All tests in `project/test_dateparser.py` must pass.
6. Do not change function signatures.

## Current State

- `project/dateparser.py` has a `parse_date(date_string)` function.
- It works for naive dates and "Z" suffix but crashes on "+HH:MM" offsets.
- `project/test_dateparser.py` has tests covering all formats.

## Files

- `project/dateparser.py` — the buggy date parser
- `project/test_dateparser.py` — test file with timezone offset test cases
