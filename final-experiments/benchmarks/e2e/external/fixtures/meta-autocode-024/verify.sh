#!/usr/bin/env bash
set -e
echo "=== TASK-024: HTTP Monitor Status Code Range Fix ==="
echo "Pattern: louislam/uptime-kuma HTTP monitor 2xx range"
echo ""
[ -f "src/heartbeat.py" ] || { echo "FAIL: heartbeat.py not found"; exit 1; }
python -m pytest tests/test_heartbeat.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: compute_status() accepts full 2xx range." || echo "FAIL"
exit $TEST_EXIT
