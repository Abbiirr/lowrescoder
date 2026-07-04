#!/usr/bin/env bash
set -e
echo "=== TASK-055: axios Case-Insensitive Header Lookup Fix ==="
[ -f "src/header_checker.py" ] || { echo "FAIL: header_checker.py not found"; exit 1; }
python -m pytest tests/test_header_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: has_header() is case-insensitive." || echo "FAIL"
exit $TEST_EXIT
