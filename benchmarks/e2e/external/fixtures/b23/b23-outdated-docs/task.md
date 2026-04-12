# Task: Fix README to Match Actual CLI Interface

## Objective

The `README.md` has outdated usage instructions that do not match the actual CLI tool in `cli.py`. Update the README so its examples match the real `--help` output.

## Requirements

1. Every command example in README.md must work with the actual CLI.
2. The CLI flag names, argument order, and subcommand names in README must match `cli.py --help` output.
3. The README must still describe all available subcommands: `init`, `build`, `deploy`, `status`.
4. The example outputs shown in README must be realistic for the actual commands.
5. Do NOT change `cli.py` — only update `README.md`.

## Current State

- `cli.py` — CLI tool with 4 subcommands. The actual interface.
- `README.md` — Documentation with wrong flag names and outdated subcommand syntax.

## Specific Discrepancies

The README contains several errors. Compare it against `python cli.py --help` and each subcommand's `--help` to find and fix them.

## Files

- `cli.py` — The CLI tool (DO NOT MODIFY)
- `README.md` — Documentation to fix
