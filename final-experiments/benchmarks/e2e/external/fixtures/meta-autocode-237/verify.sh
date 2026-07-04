#!/usr/bin/env bash
set -e
echo "=== TASK-237: parse_query_int None Handling Fix ==="
[ -f "src/query_param.py" ] || { echo "FAIL: query_param.py not found"; exit 1; }
python -m pytest tests/test_query_param.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: parse_query_int() handles None." || echo "FAIL"
exit $TEST_EXIT
