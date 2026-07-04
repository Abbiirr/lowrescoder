#!/usr/bin/env bash
set -e
echo "=== TASK-166: Value Clamping Bounds Fix ==="
[ -f "src/value_clamp.py" ] || { echo "FAIL: value_clamp.py not found"; exit 1; }
python -m pytest tests/test_value_clamp.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: clamp() returns correct boundary values." || echo "FAIL"
exit $TEST_EXIT
