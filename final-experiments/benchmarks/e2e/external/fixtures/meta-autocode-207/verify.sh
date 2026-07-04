#!/usr/bin/env bash
set -e
echo "=== TASK-207: Env Var Default Fix ==="
[ -f "src/env_resolver.py" ] || { echo "FAIL: env_resolver.py not found"; exit 1; }
python -m pytest tests/test_env_resolver.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_env_var() returns default when key is missing." || echo "FAIL"
exit $TEST_EXIT
