# TASK-011: Fix Semver String Comparison (vite/langflow pattern)

## Source
Inspired by vitejs/vite and langflow-ai/langflow version compatibility checks.
Comparing version strings lexicographically is a classic Python trap:
"1.10.0" < "1.9.0" under string ordering because "1" < "9" char-by-char.

## Goal
Fix `src/semver.py` so `is_newer()` and `latest()` use numeric tuple comparison.

## The bug
```python
# BUG: string comparison
return version_a > version_b          # "1.10.0" < "1.9.0" — wrong!
return max(versions)                  # max() on strings — wrong!

# Fix: use parse_version() (already defined in the file):
return parse_version(version_a) > parse_version(version_b)
return max(versions, key=parse_version)
```

## All 8 tests must pass
```
test_minor_double_digit_is_newer  ← FAILS ("1.10.0" < "1.9.0" as strings)
test_patch_double_digit_is_newer  ← FAILS
test_major_is_newer               ← passes (single digit: "2" > "1")
test_multi_digit_major            ← FAILS ("10" < "9" as strings)
test_equal_versions_not_newer     ← passes
test_lower_is_not_newer           ← passes
test_v_prefix_stripped            ← FAILS (v prefix breaks string compare)
test_latest_picks_correct         ← FAILS
```
