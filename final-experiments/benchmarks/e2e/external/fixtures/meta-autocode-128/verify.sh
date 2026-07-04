#!/usr/bin/env bash
set -e
echo "=== TASK-128: Connection Pool Health Check Fix ==="
[ -f "src/connection_pool.py" ] || { echo "FAIL: connection_pool.py not found"; exit 1; }
python -m pytest tests/test_connection_pool.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_connection() skips unhealthy connections." || echo "FAIL"
exit $TEST_EXIT
