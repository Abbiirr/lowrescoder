#!/usr/bin/env bash
set -e
echo "=== TASK-115: fastapi Email Validator TLD Length Fix ==="
[ -f "src/format_checker.py" ] || { echo "FAIL: format_checker.py not found"; exit 1; }
python -m pytest tests/test_format_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_valid_email() accepts 2+ char TLDs." || echo "FAIL"
exit $TEST_EXIT
