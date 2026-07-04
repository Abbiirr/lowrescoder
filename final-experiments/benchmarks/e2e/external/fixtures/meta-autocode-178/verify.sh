#!/usr/bin/env bash
set -e
echo "=== TASK-178: Max Line Length Fix ==="
[ -f "src/line_analyzer.py" ] || { echo "FAIL: line_analyzer.py not found"; exit 1; }
python -m pytest tests/test_line_analyzer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: max_line_length() includes all lines." || echo "FAIL"
exit $TEST_EXIT
