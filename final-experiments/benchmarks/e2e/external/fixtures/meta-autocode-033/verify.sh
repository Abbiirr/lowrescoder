#!/usr/bin/env bash
set -e
echo "=== TASK-033: uptime-kuma Response Time Average Fix ==="
echo "Pattern: louislam/uptime-kuma monitor response time avg"
echo ""
[ -f "src/response_time.py" ] || { echo "FAIL: response_time.py not found"; exit 1; }
python -m pytest tests/test_response_time.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: calculate_avg_response_time() excludes zeros." || echo "FAIL"
exit $TEST_EXIT
