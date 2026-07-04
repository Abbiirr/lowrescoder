#!/usr/bin/env bash
set -e
echo "=== TASK-140: Alert Throttler Time Unit Fix ==="
[ -f "src/alert_throttler.py" ] || { echo "FAIL: alert_throttler.py not found"; exit 1; }
python -m pytest tests/test_alert_throttler.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: should_send_alert() converts cooldown_minutes to seconds." || echo "FAIL"
exit $TEST_EXIT
