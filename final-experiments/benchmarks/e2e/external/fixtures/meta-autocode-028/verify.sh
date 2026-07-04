#!/usr/bin/env bash
set -e
echo "=== TASK-028: bat Line Range Single-Line Fix ==="
echo "Pattern: sharkdp/bat --line-range start==end"
echo ""
[ -f "src/line_range.py" ] || { echo "FAIL: line_range.py not found"; exit 1; }
python -m pytest tests/test_line_range.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: filter_lines() handles single-line ranges." || echo "FAIL"
exit $TEST_EXIT
