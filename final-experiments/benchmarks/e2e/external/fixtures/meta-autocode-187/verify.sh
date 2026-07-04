#!/usr/bin/env bash
set -e
echo "=== TASK-187: Line Counter Fix ==="
[ -f "src/line_counter.py" ] || { echo "FAIL: line_counter.py not found"; exit 1; }
python -m pytest tests/test_line_counter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: count_lines() handles empty string and trailing newline correctly." || echo "FAIL"
exit $TEST_EXIT
