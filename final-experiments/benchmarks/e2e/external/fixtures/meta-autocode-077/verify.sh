#!/usr/bin/env bash
set -e
echo "=== TASK-077: bat Line Number Padding Width Fix ==="
[ -f "src/line_formatter.py" ] || { echo "FAIL: line_formatter.py not found"; exit 1; }
python -m pytest tests/test_line_formatter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: format_line_number() uses len(str(total_lines)) for width." || echo "FAIL"
exit $TEST_EXIT
