#!/usr/bin/env bash
set -e
echo "=== TASK-249: get_monitor_url Wrong Key Fix ==="
[ -f "src/monitor_url.py" ] || { echo "FAIL: monitor_url.py not found"; exit 1; }
python -m pytest tests/test_monitor_url.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_monitor_url() reads 'url' key." || echo "FAIL"
exit $TEST_EXIT
