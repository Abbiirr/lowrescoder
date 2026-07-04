#!/usr/bin/env bash
set -e
echo "=== TASK-122: Syntax Highlighter Range Boundary Fix ==="
[ -f "src/syntax_highlighter.py" ] || { echo "FAIL: syntax_highlighter.py not found"; exit 1; }
python -m pytest tests/test_syntax_highlighter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_highlight_lines() uses inclusive range_end." || echo "FAIL"
exit $TEST_EXIT
