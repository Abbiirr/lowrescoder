#!/usr/bin/env bash
set -e
echo "=== TASK-063: FastAPI Rate Limiter Boundary Fix ==="
[ -f "src/rate_limiter.py" ] || { echo "FAIL: rate_limiter.py not found"; exit 1; }
python -m pytest tests/test_rate_limiter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_rate_limited() blocks at exactly the limit (>=)." || echo "FAIL"
exit $TEST_EXIT
