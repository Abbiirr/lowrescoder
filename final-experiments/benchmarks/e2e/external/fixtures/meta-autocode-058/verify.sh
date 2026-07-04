#!/usr/bin/env bash
set -e
echo "=== TASK-058: FastAPI Integer Range Bound Validation Fix ==="
[ -f "src/range_validator.py" ] || { echo "FAIL: range_validator.py not found"; exit 1; }
python -m pytest tests/test_range_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: validate_int_range() raises ValueError for out-of-bound values." || echo "FAIL"
exit $TEST_EXIT
