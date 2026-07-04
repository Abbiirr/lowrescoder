#!/usr/bin/env bash
set -e
echo "=== TASK-227: count_output_edges Source Filter Fix ==="
[ -f "src/edge_counter.py" ] || { echo "FAIL: edge_counter.py not found"; exit 1; }
python -m pytest tests/test_edge_counter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: count_output_edges() filters by source." || echo "FAIL"
exit $TEST_EXIT
