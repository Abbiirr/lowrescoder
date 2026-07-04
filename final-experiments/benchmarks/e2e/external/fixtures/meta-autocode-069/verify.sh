#!/usr/bin/env bash
set -e
echo "=== TASK-069: memos Default Memo Visibility Fix ==="
[ -f "src/memo_creator.py" ] || { echo "FAIL: memo_creator.py not found"; exit 1; }
python -m pytest tests/test_memo_creator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: create_memo() defaults visibility to 'private'." || echo "FAIL"
exit $TEST_EXIT
