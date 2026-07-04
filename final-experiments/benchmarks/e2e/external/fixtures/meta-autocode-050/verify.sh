#!/usr/bin/env bash
set -e
echo "=== TASK-050: Vite Client Env Var Prefix Filter Fix ==="
[ -f "src/env_filter.py" ] || { echo "FAIL: env_filter.py not found"; exit 1; }
python -m pytest tests/test_env_filter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_client_env_vars() filters to VITE_ prefix." || echo "FAIL"
exit $TEST_EXIT
