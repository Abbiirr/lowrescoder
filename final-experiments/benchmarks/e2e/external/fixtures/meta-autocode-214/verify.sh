#!/usr/bin/env bash
set -e
echo "=== TASK-214: format_line_number Padding Fix ==="
[ -f "src/line_formatter.py" ] || { echo "FAIL: line_formatter.py not found"; exit 1; }
python -m pytest tests/test_line_formatter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: format_line_number() right-justifies." || echo "FAIL"
exit $TEST_EXIT
