#!/usr/bin/env bash
set -e
echo "=== TASK-211: get_query_string No-Query Fix ==="
[ -f "src/query_parser.py" ] || { echo "FAIL: query_parser.py not found"; exit 1; }
python -m pytest tests/test_query_parser.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_query_string() handles missing query." || echo "FAIL"
exit $TEST_EXIT
