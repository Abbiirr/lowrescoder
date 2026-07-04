#!/usr/bin/env bash
set -e
echo "=== TASK-092: uptime-kuma Session Expiry TTL Unit Fix ==="
[ -f "src/session_expiry.py" ] || { echo "FAIL: session_expiry.py not found"; exit 1; }
python -m pytest tests/test_session_expiry.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_session_expired() converts ttl_minutes to seconds." || echo "FAIL"
exit $TEST_EXIT
