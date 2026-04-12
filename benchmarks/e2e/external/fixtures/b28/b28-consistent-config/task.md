# Task: Build a Consistent Config Merger

## Objective

Build a config merger that produces the same output regardless of the order the input files are provided. The merger should combine 3 JSON config files with deterministic conflict resolution.

## Requirements

1. Implement `merge_configs(config_paths)` in `project/merger.py`.
2. The merge output must be identical regardless of input file order.
3. Conflict resolution: when keys conflict, use alphabetically-last file's value (deterministic).
4. Nested objects should be deep-merged.
5. The result must match `project/expected_merged.json`.
6. All tests in `project/test_merger.py` must pass.

## Files

- `project/merger.py` — implement the merger here
- `project/config_a.json`, `project/config_b.json`, `project/config_c.json` — configs to merge
- `project/expected_merged.json` — expected merge result
- `project/test_merger.py` — test file
