#!/usr/bin/env bash
set -e
echo "=== TASK-192: Param Name Keyword Check Fix ==="
[ -f "src/param_checker.py" ] || { echo "FAIL: param_checker.py not found"; exit 1; }
python -m pytest tests/test_param_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_valid_param_name() rejects Python keywords." || echo "FAIL"
exit $TEST_EXIT
