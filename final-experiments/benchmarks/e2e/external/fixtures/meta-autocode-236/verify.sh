#!/usr/bin/env bash
set -e
echo "=== TASK-236: get_node_inputs Key Fix ==="
[ -f "src/node_inputs.py" ] || { echo "FAIL: node_inputs.py not found"; exit 1; }
python -m pytest tests/test_node_inputs.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_node_inputs() reads 'inputs'." || echo "FAIL"
exit $TEST_EXIT
