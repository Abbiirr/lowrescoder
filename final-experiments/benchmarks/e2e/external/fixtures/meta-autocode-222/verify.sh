#!/usr/bin/env bash
set -e
echo "=== TASK-222: format_duration Minutes Remainder Fix ==="
[ -f "src/duration_formatter.py" ] || { echo "FAIL: duration_formatter.py not found"; exit 1; }
python -m pytest tests/test_duration_formatter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: format_duration() shows remainder minutes." || echo "FAIL"
exit $TEST_EXIT
