# Task: Resolve Dependency Conflicts

## Objective

Fix a broken `requirements_broken.txt` that has conflicting version constraints.

## Requirements

1. Read `requirements_broken.txt` and identify all conflicting constraints.
2. Write `requirements_fixed.txt` with resolved constraints:
   - Each package appears exactly ONCE
   - No two constraints for the same package conflict
   - When two ranges conflict, prefer the NEWER version range
   - Keep non-conflicting packages unchanged
   - Skip comment lines (lines starting with #) and blank lines
3. Write `conflict_report.txt` explaining:
   - Which packages had conflicts
   - What the conflicting constraints were
   - How each was resolved
4. Run with `python resolve.py`.

## Conflicts in requirements_broken.txt

- `sqlalchemy`: `>=1.4,<2.0` vs `>=2.0,<3.0` -- pick newer: `>=2.0,<3.0`
- `urllib3`: `>=1.26,<2.0` vs `>=2.0` -- pick newer: `>=2.0`
- `numpy`: `>=1.24,<1.25` vs `>=1.25` -- pick newer: `>=1.25`
- `pytest`: `>=7.0` vs `<7.0` -- contradictory, pick newer: `>=7.0`

## Files

- `requirements_broken.txt` -- the broken requirements file
- `.package_versions.json` -- available package versions (for reference)
- `resolve.py` -- the script you must edit
- `requirements_fixed.txt` -- output: resolved requirements
- `conflict_report.txt` -- output: explanation of resolutions
