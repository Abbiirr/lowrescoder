#!/usr/bin/env bash
set -e
echo "=== TASK-095: memos Memo Visibility Protected Role Check Fix ==="
[ -f "src/memo_visibility.py" ] || { echo "FAIL: memo_visibility.py not found"; exit 1; }
python -m pytest tests/test_memo_visibility.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: can_view_memo() blocks public role from protected memos." || echo "FAIL"
exit $TEST_EXIT
