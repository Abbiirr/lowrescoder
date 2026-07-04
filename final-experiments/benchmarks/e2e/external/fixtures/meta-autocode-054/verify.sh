#!/usr/bin/env bash
set -e
echo "=== TASK-054: uptime-kuma Heartbeat Interval Minimum Fix ==="
[ -f "src/heartbeat_validator.py" ] || { echo "FAIL: heartbeat_validator.py not found"; exit 1; }
python -m pytest tests/test_heartbeat_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: validate_heartbeat_interval() enforces >= 20s minimum." || echo "FAIL"
exit $TEST_EXIT
