#!/usr/bin/env bash
set -e
echo "=== TASK-010: URL Builder urljoin Fix ==="
echo "Pattern: axios/axios URL construction (harness-bench v2)"
echo ""
[ -f "src/api_client.py" ] || { echo "FAIL: api_client.py not found"; exit 1; }
python -m pytest tests/test_api_client.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: build_url correctly appends endpoint to base path." || echo "FAIL"
exit $TEST_EXIT
