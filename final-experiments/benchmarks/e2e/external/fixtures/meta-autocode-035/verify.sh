#!/usr/bin/env bash
set -e
echo "=== TASK-035: FastAPI List Query Param Parsing Fix ==="
echo "Pattern: fastapi/fastapi repeated query parameter collection"
echo ""
[ -f "src/query_list.py" ] || { echo "FAIL: query_list.py not found"; exit 1; }
python -m pytest tests/test_query_list.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: parse_list_query_param() collects all occurrences." || echo "FAIL"
exit $TEST_EXIT
