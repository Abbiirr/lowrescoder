#!/usr/bin/env bash
set -e
echo "=== TASK-118: Interceptor Chain Order Fix ==="
[ -f "src/interceptor_chain.py" ] || { echo "FAIL: interceptor_chain.py not found"; exit 1; }
python -m pytest tests/test_interceptor_chain.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: apply_interceptors() preserves insertion order." || echo "FAIL"
exit $TEST_EXIT
