#!/usr/bin/env bash
set -e
echo "=== TASK-208: Main Branch Check Fix ==="
[ -f "src/branch_checker.py" ] || { echo "FAIL: branch_checker.py not found"; exit 1; }
python -m pytest tests/test_branch_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_main_branch() uses exact equality." || echo "FAIL"
exit $TEST_EXIT
