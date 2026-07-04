#!/usr/bin/env bash
set -e
echo "=== TASK-177: Uptime Percentage Case-Insensitive Fix ==="
[ -f "src/uptime_calculator.py" ] || { echo "FAIL: uptime_calculator.py not found"; exit 1; }
python -m pytest tests/test_uptime_calculator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: uptime_percentage() handles mixed-case status strings." || echo "FAIL"
exit $TEST_EXIT
