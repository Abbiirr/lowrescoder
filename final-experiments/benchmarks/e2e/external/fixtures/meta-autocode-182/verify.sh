#!/usr/bin/env bash
set -e
echo "=== TASK-182: Range Check Max-Inclusive Fix ==="
[ -f "src/param_validator.py" ] || { echo "FAIL: param_validator.py not found"; exit 1; }
python -m pytest tests/test_param_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_in_range() includes max_val as valid." || echo "FAIL"
exit $TEST_EXIT
