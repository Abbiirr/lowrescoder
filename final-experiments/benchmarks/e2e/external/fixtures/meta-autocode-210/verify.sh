#!/usr/bin/env bash
set -e
echo "=== TASK-210: is_valid_email Structural Validation Fix ==="
[ -f "src/email_validator.py" ] || { echo "FAIL: email_validator.py not found"; exit 1; }
python -m pytest tests/test_email_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_valid_email() validates structure." || echo "FAIL"
exit $TEST_EXIT
