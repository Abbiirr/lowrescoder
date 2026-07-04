#!/usr/bin/env bash
set -e
echo "=== TASK-103: fastapi Response Success Flag 2xx Range Fix ==="
[ -f "src/response_builder.py" ] || { echo "FAIL: response_builder.py not found"; exit 1; }
python -m pytest tests/test_response_builder.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: build_api_response() sets success for 200-299 range." || echo "FAIL"
exit $TEST_EXIT
