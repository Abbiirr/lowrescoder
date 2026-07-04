#!/usr/bin/env bash
set -e
echo "=== TASK-245: get_node_outputs Wrong Key Fix ==="
[ -f "src/node_outputs.py" ] || { echo "FAIL: node_outputs.py not found"; exit 1; }
python -m pytest tests/test_node_outputs.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_node_outputs() reads 'outputs' key." || echo "FAIL"
exit $TEST_EXIT
