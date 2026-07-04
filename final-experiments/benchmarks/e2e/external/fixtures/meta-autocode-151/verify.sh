#!/usr/bin/env bash
set -e
echo "=== TASK-151: Query String Parsing Fix ==="
[ -f "src/query_parser.py" ] || { echo "FAIL: query_parser.py not found"; exit 1; }
python -m pytest tests/test_query_parser.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: parse_query_string() handles '=' in values." || echo "FAIL"
exit $TEST_EXIT
