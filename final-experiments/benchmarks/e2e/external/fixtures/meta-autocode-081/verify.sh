#!/usr/bin/env bash
set -e
echo "=== TASK-081: bat Line Numbering Start Offset Fix ==="
[ -f "src/line_numberer.py" ] || { echo "FAIL: line_numberer.py not found"; exit 1; }
python -m pytest tests/test_line_numberer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: number_lines() respects start parameter." || echo "FAIL"
exit $TEST_EXIT
