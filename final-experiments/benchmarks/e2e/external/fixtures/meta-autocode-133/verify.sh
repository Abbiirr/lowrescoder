#!/usr/bin/env bash
set -e
echo "=== TASK-133: Status Aggregator Up/Down Count Fix ==="
[ -f "src/status_aggregator.py" ] || { echo "FAIL: status_aggregator.py not found"; exit 1; }
python -m pytest tests/test_status_aggregator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: compute_uptime_percent() counts 'up' checks." || echo "FAIL"
exit $TEST_EXIT
