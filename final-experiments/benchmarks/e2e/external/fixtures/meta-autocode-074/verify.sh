#!/usr/bin/env bash
set -e
echo "=== TASK-074: memos Archived Memo Filtering Fix ==="
[ -f "src/memo_filter.py" ] || { echo "FAIL: memo_filter.py not found"; exit 1; }
python -m pytest tests/test_memo_filter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: filter_memos() excludes archived memos by default." || echo "FAIL"
exit $TEST_EXIT
