#!/usr/bin/env bash
set -e
echo "=== TASK-215: get_memo_tags Wrong Key Fix ==="
[ -f "src/memo_tags.py" ] || { echo "FAIL: memo_tags.py not found"; exit 1; }
python -m pytest tests/test_memo_tags.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_memo_tags() reads correct key." || echo "FAIL"
exit $TEST_EXIT
