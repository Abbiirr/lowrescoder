#!/usr/bin/env bash
set -e
echo "=== TASK-052: FastAPI Response Exclude None Fix ==="
[ -f "src/response_serializer.py" ] || { echo "FAIL: response_serializer.py not found"; exit 1; }
python -m pytest tests/test_response_serializer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: serialize_response() honours exclude_none flag." || echo "FAIL"
exit $TEST_EXIT
