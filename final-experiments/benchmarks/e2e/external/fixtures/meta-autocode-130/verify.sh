#!/usr/bin/env bash
set -e
echo "=== TASK-130: Flow Node Validator Edge Direction Fix ==="
[ -f "src/node_validator.py" ] || { echo "FAIL: node_validator.py not found"; exit 1; }
python -m pytest tests/test_node_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: validate_flow_nodes() checks out-edges for source nodes." || echo "FAIL"
exit $TEST_EXIT
