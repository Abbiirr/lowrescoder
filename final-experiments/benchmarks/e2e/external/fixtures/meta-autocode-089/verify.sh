#!/usr/bin/env bash
set -e
echo "=== TASK-089: langflow Flow Nodes Type Validation Fix ==="
[ -f "src/flow_validator.py" ] || { echo "FAIL: flow_validator.py not found"; exit 1; }
python -m pytest tests/test_flow_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: validate_flow_inputs() checks nodes is a list." || echo "FAIL"
exit $TEST_EXIT
