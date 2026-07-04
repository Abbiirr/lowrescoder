#!/usr/bin/env bash
set -e
echo "=== TASK-197: Latest Memo Sort Fix ==="
[ -f "src/memo_sorter.py" ] || { echo "FAIL: memo_sorter.py not found"; exit 1; }
python -m pytest tests/test_memo_sorter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_latest_memo() returns the most recently updated memo." || echo "FAIL"
exit $TEST_EXIT
