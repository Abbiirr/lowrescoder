# Task: Fix a Broken Bash Build Script

## Objective

The `build.sh` script in the project has several bugs that prevent it from working correctly. Fix all bugs.

## Requirements

1. `build.sh` must exit 0 when run successfully.
2. The script must create a `dist/` directory with compiled output.
3. The script must handle spaces in directory names correctly.
4. The script must not use deprecated bash features (no backticks for command substitution).
5. All variable expansions must be properly quoted.

## Current Bugs

- Unquoted variable in `cp` command causes failure with spaces in paths
- Uses backticks instead of `$()` for command substitution
- Missing `-p` flag on `mkdir` (fails if parent doesn't exist)
- Exit code not checked after compilation step

## Files

- `build.sh` — the broken build script
- `src/` — source files to compile
