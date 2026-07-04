#!/usr/bin/env bash
set -e
echo "=== TASK-080: uptime-kuma Monitor Last Check Timestamp Fix ==="
[ -f "src/monitor_updater.py" ] || { echo "FAIL: monitor_updater.py not found"; exit 1; }
python -m pytest tests/test_monitor_updater.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: update_monitor_status() always updates last_check." || echo "FAIL"
exit $TEST_EXIT
