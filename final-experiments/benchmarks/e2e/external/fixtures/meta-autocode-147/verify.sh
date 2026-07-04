#!/usr/bin/env bash
set -e
echo "=== TASK-147: HTTP Retry Status Check Fix ==="
[ -f "src/http_retry.py" ] || { echo "FAIL: http_retry.py not found"; exit 1; }
python -m pytest tests/test_http_retry.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: should_retry() retries on 5xx not 200." || echo "FAIL"
exit $TEST_EXIT
