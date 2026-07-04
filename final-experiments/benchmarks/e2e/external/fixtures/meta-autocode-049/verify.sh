#!/usr/bin/env bash
set -e
echo "=== TASK-049: bat Tab Width Expansion Fix ==="
[ -f "src/tab_expander.py" ] || { echo "FAIL: tab_expander.py not found"; exit 1; }
python -m pytest tests/test_tab_expander.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: expand_tabs() uses tab_width parameter." || echo "FAIL"
exit $TEST_EXIT
