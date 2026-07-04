#!/usr/bin/env bash
set -e
echo "=== TASK-231: format_uptime_percent Division Fix ==="
[ -f "src/uptime_percent.py" ] || { echo "FAIL: uptime_percent.py not found"; exit 1; }
python -m pytest tests/test_uptime_percent.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: format_uptime_percent() divides up/total." || echo "FAIL"
exit $TEST_EXIT
