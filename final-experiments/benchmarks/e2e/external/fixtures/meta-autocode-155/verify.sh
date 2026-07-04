#!/usr/bin/env bash
set -e
echo "=== TASK-155: HTTP Method Validation Fix ==="
[ -f "src/http_validator.py" ] || { echo "FAIL: http_validator.py not found"; exit 1; }
python -m pytest tests/test_http_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_valid_method() accepts any case." || echo "FAIL"
exit $TEST_EXIT
