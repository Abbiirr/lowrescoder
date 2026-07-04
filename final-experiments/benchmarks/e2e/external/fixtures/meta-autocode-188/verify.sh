#!/usr/bin/env bash
set -e
echo "=== TASK-188: Memo Pinned Check Fix ==="
[ -f "src/memo_pin.py" ] || { echo "FAIL: memo_pin.py not found"; exit 1; }
python -m pytest tests/test_memo_pin.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_pinned() reads 'is_pinned' field correctly." || echo "FAIL"
exit $TEST_EXIT
