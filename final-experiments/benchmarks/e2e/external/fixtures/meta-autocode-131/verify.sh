#!/usr/bin/env bash
set -e
echo "=== TASK-131: JSON Serializer Nested None Fix ==="
[ -f "src/json_serializer.py" ] || { echo "FAIL: json_serializer.py not found"; exit 1; }
python -m pytest tests/test_json_serializer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: serialize_response() recursively excludes None values." || echo "FAIL"
exit $TEST_EXIT
