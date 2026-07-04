#!/usr/bin/env bash
set -e
echo "=== TASK-232: is_empty_line Whitespace Fix ==="
[ -f "src/line_checker.py" ] || { echo "FAIL: line_checker.py not found"; exit 1; }
python -m pytest tests/test_line_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_empty_line() treats whitespace-only as empty." || echo "FAIL"
exit $TEST_EXIT
