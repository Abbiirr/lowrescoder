#!/usr/bin/env bash
set -e
echo "=== TASK-039: langflow Input Validator Max Inclusive Fix ==="
echo "Pattern: langflow-ai/langflow component input max boundary"
echo ""
[ -f "src/input_validator.py" ] || { echo "FAIL: input_validator.py not found"; exit 1; }
python -m pytest tests/test_input_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: validate_numeric_input() treats max_val as inclusive." || echo "FAIL"
exit $TEST_EXIT
