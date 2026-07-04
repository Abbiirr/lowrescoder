#!/usr/bin/env bash
set -e
echo "=== TASK-060: langflow Flow Timeout Default Fix ==="
[ -f "src/timeout_resolver.py" ] || { echo "FAIL: timeout_resolver.py not found"; exit 1; }
python -m pytest tests/test_timeout_resolver.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: resolve_timeout() returns DEFAULT_TIMEOUT for non-positive values." || echo "FAIL"
exit $TEST_EXIT
