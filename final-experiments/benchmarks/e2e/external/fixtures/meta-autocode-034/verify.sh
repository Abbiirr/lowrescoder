#!/usr/bin/env bash
set -e
echo "=== TASK-034: memos Visibility Filter Case-Insensitive Fix ==="
echo "Pattern: usememos/memos visibility filter API"
echo ""
[ -f "src/memo_visibility.py" ] || { echo "FAIL: memo_visibility.py not found"; exit 1; }
python -m pytest tests/test_memo_visibility.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: filter_by_visibility() is case-insensitive." || echo "FAIL"
exit $TEST_EXIT
