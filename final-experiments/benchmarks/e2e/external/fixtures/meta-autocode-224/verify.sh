#!/usr/bin/env bash
set -e
echo "=== TASK-224: is_memo_public Uppercase Fix ==="
[ -f "src/memo_visibility.py" ] || { echo "FAIL: memo_visibility.py not found"; exit 1; }
python -m pytest tests/test_memo_visibility.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_memo_public() checks 'PUBLIC'." || echo "FAIL"
exit $TEST_EXIT
