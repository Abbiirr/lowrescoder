#!/usr/bin/env bash
set -e
echo "=== TASK-027: Langflow Type Validator Any Wildcard Fix ==="
echo "Pattern: langflow-ai/langflow connection type Any wildcard"
echo ""
[ -f "src/type_validator.py" ] || { echo "FAIL: type_validator.py not found"; exit 1; }
python -m pytest tests/test_type_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: can_connect() handles Any wildcard." || echo "FAIL"
exit $TEST_EXIT
