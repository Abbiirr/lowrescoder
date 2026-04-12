# Task: Update Config Format v1 to v2 With Backward Compatibility

## Objective

Update the config parser in `configparser_app.py` to support both v1 and v2 config formats. Existing v1 configs must continue to work unchanged.

## Requirements

1. v1 format configs (INI-style `key = value`) must still parse correctly.
2. v2 format configs (YAML-style nested `section:\n  key: value`) must also parse correctly.
3. The parser must auto-detect the format (v1 vs v2) based on file content.
4. All existing tests in `test_configparser.py` must pass without modification.
5. The public function `parse_config(filepath)` signature must not change.
6. The return type remains `dict[str, dict[str, str]]` — a dict of sections, each containing key-value pairs.

## v2 Format Specification

```yaml
database:
  host: localhost
  port: 5432
  name: mydb
server:
  host: 0.0.0.0
  port: 8080
```

Values are always strings (same as v1). Sections are top-level keys ending with `:`. Entries under a section are indented with 2 spaces and use `key: value` format.

## Current State

- `configparser_app.py` — Config parser that only handles v1 (INI-style) format.
- `test_configparser.py` — Tests using v1 format configs.
- `sample_v1.conf` — Example v1 config used by tests.
- `sample_v2.conf` — Example v2 config (provided for reference, no tests yet).

## Files

- `configparser_app.py` — Parser to extend
- `test_configparser.py` — Existing tests (must not be modified)
- `sample_v1.conf` — v1 format example
- `sample_v2.conf` — v2 format example
