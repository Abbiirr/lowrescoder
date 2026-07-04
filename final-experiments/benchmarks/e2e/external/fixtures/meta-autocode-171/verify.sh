#!/usr/bin/env bash
set -e
echo "=== TASK-171: Leading Zero Strip Fix ==="
[ -f "src/string_cleaner.py" ] || { echo "FAIL: string_cleaner.py not found"; exit 1; }
python -m pytest tests/test_string_cleaner.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: strip_leading_zeros() returns '0' for all-zero inputs." || echo "FAIL"
exit $TEST_EXIT
