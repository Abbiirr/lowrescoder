#!/usr/bin/env bash
set -e
echo "=== TASK-156: Percentage Calculation Float Division Fix ==="
[ -f "src/metrics_calculator.py" ] || { echo "FAIL: metrics_calculator.py not found"; exit 1; }
python -m pytest tests/test_metrics_calculator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: calculate_percentage() returns float." || echo "FAIL"
exit $TEST_EXIT
