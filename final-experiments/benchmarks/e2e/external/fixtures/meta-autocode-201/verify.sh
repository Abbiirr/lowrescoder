#!/usr/bin/env bash
set -e
echo "=== TASK-201: Pagination Limit Fix ==="
[ -f "src/pagination.py" ] || { echo "FAIL: pagination.py not found"; exit 1; }
python -m pytest tests/test_pagination.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: validate_limit() rejects values > 100." || echo "FAIL"
exit $TEST_EXIT
