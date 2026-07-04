#!/usr/bin/env bash
set -e
echo "=== TASK-037: axios Retry Policy 5xx Fix ==="
echo "Pattern: axios/axios retry on server error status codes"
echo ""
[ -f "src/retry_policy.py" ] || { echo "FAIL: retry_policy.py not found"; exit 1; }
python -m pytest tests/test_retry_policy.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: should_retry() handles all 5xx codes." || echo "FAIL"
exit $TEST_EXIT
