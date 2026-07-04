#!/usr/bin/env bash
set -e
echo "=== TASK-195: Health Threshold Fix ==="
[ -f "src/health_checker.py" ] || { echo "FAIL: health_checker.py not found"; exit 1; }
python -m pytest tests/test_health_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_healthy() uses 99.5% threshold." || echo "FAIL"
exit $TEST_EXIT
