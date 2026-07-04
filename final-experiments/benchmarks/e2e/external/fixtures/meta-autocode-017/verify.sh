#!/usr/bin/env bash
set -e
echo "=== TASK-017: Flow Node Topological Sort Fix ==="
echo "Pattern: langflow-ai/langflow DAG execution"
echo ""
[ -f "src/flow_sorter.py" ] || { echo "FAIL: flow_sorter.py not found"; exit 1; }
python -m pytest tests/test_flow_sorter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: topological_sort() seeds all source nodes." || echo "FAIL"
exit $TEST_EXIT
