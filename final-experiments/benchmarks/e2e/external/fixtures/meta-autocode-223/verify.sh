#!/usr/bin/env bash
set -e
echo "=== TASK-223: replace_tabs Width Fix ==="
[ -f "src/tab_replacer.py" ] || { echo "FAIL: tab_replacer.py not found"; exit 1; }
python -m pytest tests/test_tab_replacer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: replace_tabs() uses width parameter." || echo "FAIL"
exit $TEST_EXIT
