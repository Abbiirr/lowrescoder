#!/usr/bin/env bash
set -e
echo "=== TASK-193: Timeout Validator Fix ==="
[ -f "src/config_validator.py" ] || { echo "FAIL: config_validator.py not found"; exit 1; }
python -m pytest tests/test_config_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: has_valid_timeout() requires timeout > 0." || echo "FAIL"
exit $TEST_EXIT
