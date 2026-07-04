#!/usr/bin/env bash
set -e
echo "=== TASK-120: Rate Limiter Off-By-One Fix ==="
[ -f "src/rate_limiter.py" ] || { echo "FAIL: rate_limiter.py not found"; exit 1; }
python -m pytest tests/test_rate_limiter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_allowed() permits exactly max_requests per window." || echo "FAIL"
exit $TEST_EXIT
