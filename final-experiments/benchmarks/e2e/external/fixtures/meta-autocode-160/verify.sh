#!/usr/bin/env bash
set -e
echo "=== TASK-160: Palindrome Case-Sensitivity Fix ==="
[ -f "src/string_utils.py" ] || { echo "FAIL: string_utils.py not found"; exit 1; }
python -m pytest tests/test_string_utils.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_palindrome() is case-insensitive." || echo "FAIL"
exit $TEST_EXIT
