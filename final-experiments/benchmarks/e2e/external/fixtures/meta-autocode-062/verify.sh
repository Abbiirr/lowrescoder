#!/usr/bin/env bash
set -e
echo "=== TASK-062: Memos Case-Insensitive Search Highlight Fix ==="
[ -f "src/search_highlighter.py" ] || { echo "FAIL: search_highlighter.py not found"; exit 1; }
python -m pytest tests/test_search_highlighter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: highlight_matches() is case-insensitive." || echo "FAIL"
exit $TEST_EXIT
