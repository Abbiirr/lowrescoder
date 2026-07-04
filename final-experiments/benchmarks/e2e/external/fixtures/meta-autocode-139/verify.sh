#!/usr/bin/env bash
set -e
echo "=== TASK-139: Config Validator Falsy vs None Fix ==="
[ -f "src/config_validator.py" ] || { echo "FAIL: config_validator.py not found"; exit 1; }
python -m pytest tests/test_config_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: validate_config() uses 'is None' not 'not value'." || echo "FAIL"
exit $TEST_EXIT
