#!/usr/bin/env bash
set -e
echo "=== TASK-181: Short Hash Length Fix ==="
[ -f "src/hash_utils.py" ] || { echo "FAIL: hash_utils.py not found"; exit 1; }
python -m pytest tests/test_hash_utils.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: short_hash() returns 7 characters." || echo "FAIL"
exit $TEST_EXIT
