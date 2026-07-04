#!/usr/bin/env bash
set -e
echo "=== TASK-025: Memo Search Case-Insensitive Fix ==="
echo "Pattern: usememos/memos search case sensitivity"
echo ""
[ -f "src/memo_search.py" ] || { echo "FAIL: memo_search.py not found"; exit 1; }
python -m pytest tests/test_memo_search.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: search_memo() is case-insensitive." || echo "FAIL"
exit $TEST_EXIT
