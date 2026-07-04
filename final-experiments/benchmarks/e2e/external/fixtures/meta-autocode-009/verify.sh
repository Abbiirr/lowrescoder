#!/usr/bin/env bash
set -e
echo "=== TASK-009: Incident Tracker EOF Bug Fix ==="
echo "Pattern: louislam/uptime-kuma heartbeat detection (harness-bench v2)"
echo ""
[ -f "src/incident_tracker.py" ] || { echo "FAIL: incident_tracker.py not found"; exit 1; }
python -m pytest tests/test_incident_tracker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: Ongoing incidents correctly returned at EOF." || echo "FAIL"
exit $TEST_EXIT
