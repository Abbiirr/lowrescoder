#!/usr/bin/env bash
set -e
echo "=== TASK-053: lazygit Diff Header Exclusion Fix ==="
[ -f "src/diff_counter.py" ] || { echo "FAIL: diff_counter.py not found"; exit 1; }
python -m pytest tests/test_diff_counter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: count_diff_lines() skips +++ and --- headers." || echo "FAIL"
exit $TEST_EXIT
