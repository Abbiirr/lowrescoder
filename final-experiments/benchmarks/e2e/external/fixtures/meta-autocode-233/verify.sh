#!/usr/bin/env bash
set -e
echo "=== TASK-233: get_memo_author Key Fix ==="
[ -f "src/memo_author.py" ] || { echo "FAIL: memo_author.py not found"; exit 1; }
python -m pytest tests/test_memo_author.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_memo_author() reads correct key." || echo "FAIL"
exit $TEST_EXIT
