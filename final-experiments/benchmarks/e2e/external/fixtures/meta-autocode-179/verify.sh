#!/usr/bin/env bash
set -e
echo "=== TASK-179: Public Memo Count Fix ==="
[ -f "src/memo_visibility.py" ] || { echo "FAIL: memo_visibility.py not found"; exit 1; }
python -m pytest tests/test_memo_visibility.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: count_public_memos() filters by visibility='PUBLIC'." || echo "FAIL"
exit $TEST_EXIT
