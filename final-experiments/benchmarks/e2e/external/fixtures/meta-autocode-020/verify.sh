#!/usr/bin/env bash
set -e
echo "=== TASK-020: Response Serializer Nested None Exclusion Fix ==="
echo "Pattern: fastapi/fastapi pydantic exclude_none recursion"
echo ""
[ -f "src/response_serializer.py" ] || { echo "FAIL: response_serializer.py not found"; exit 1; }
python -m pytest tests/test_response_serializer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: serialize_response() recursively strips None values." || echo "FAIL"
exit $TEST_EXIT
