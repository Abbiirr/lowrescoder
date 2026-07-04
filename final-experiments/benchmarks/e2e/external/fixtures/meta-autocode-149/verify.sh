#!/usr/bin/env bash
set -e
echo "=== TASK-149: Memo Tag Case-Insensitive Search Fix ==="
[ -f "src/memo_tagger.py" ] || { echo "FAIL: memo_tagger.py not found"; exit 1; }
python -m pytest tests/test_memo_tagger.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: find_memos_by_tag() is case-insensitive." || echo "FAIL"
exit $TEST_EXIT
