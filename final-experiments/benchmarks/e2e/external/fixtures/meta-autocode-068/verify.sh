#!/usr/bin/env bash
set -e
echo "=== TASK-068: axios Per-Request Timeout Override Fix ==="
[ -f "src/timeout_merger.py" ] || { echo "FAIL: timeout_merger.py not found"; exit 1; }
python -m pytest tests/test_timeout_merger.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: resolve_request_timeout() honours request-level override." || echo "FAIL"
exit $TEST_EXIT
