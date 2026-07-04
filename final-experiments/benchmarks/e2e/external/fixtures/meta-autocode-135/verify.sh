#!/usr/bin/env bash
set -e
echo "=== TASK-135: Diff Calculator Added Count Fix ==="
[ -f "src/diff_calculator.py" ] || { echo "FAIL: diff_calculator.py not found"; exit 1; }
python -m pytest tests/test_diff_calculator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: count_changes() only counts genuinely new lines." || echo "FAIL"
exit $TEST_EXIT
