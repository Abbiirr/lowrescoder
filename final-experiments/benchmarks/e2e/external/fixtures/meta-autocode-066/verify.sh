#!/usr/bin/env bash
set -e
echo "=== TASK-066: uptime-kuma HTTP 2xx Status Range Fix ==="
[ -f "src/status_checker.py" ] || { echo "FAIL: status_checker.py not found"; exit 1; }
python -m pytest tests/test_status_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_status_ok() accepts full 2xx range." || echo "FAIL"
exit $TEST_EXIT
