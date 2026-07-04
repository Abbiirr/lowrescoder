#!/usr/bin/env bash
set -e
echo "=== TASK-019: HTTP Client Interceptor LIFO Order Fix ==="
echo "Pattern: axios/axios request interceptor dispatch"
echo ""
[ -f "src/http_client.py" ] || { echo "FAIL: http_client.py not found"; exit 1; }
python -m pytest tests/test_http_client.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: request() applies interceptors in LIFO order." || echo "FAIL"
exit $TEST_EXIT
