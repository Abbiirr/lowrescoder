#!/usr/bin/env bash
set -e
echo "=== TASK-225: get_port Config Key Fix ==="
[ -f "src/server_config.py" ] || { echo "FAIL: server_config.py not found"; exit 1; }
python -m pytest tests/test_server_config.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_port() reads correct key." || echo "FAIL"
exit $TEST_EXIT
