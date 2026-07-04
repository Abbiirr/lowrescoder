#!/usr/bin/env bash
set -e
echo "=== TASK-220: strip_auth_header Case-Insensitive Fix ==="
[ -f "src/header_utils.py" ] || { echo "FAIL: header_utils.py not found"; exit 1; }
python -m pytest tests/test_header_utils.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: strip_auth_header() handles all casings." || echo "FAIL"
exit $TEST_EXIT
