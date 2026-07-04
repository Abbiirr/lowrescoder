#!/usr/bin/env bash
set -e
echo "=== TASK-204: Stale Alert Check Fix ==="
[ -f "src/alert_checker.py" ] || { echo "FAIL: alert_checker.py not found"; exit 1; }
python -m pytest tests/test_alert_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_stale_alert() uses >= threshold comparison." || echo "FAIL"
exit $TEST_EXIT
