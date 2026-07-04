#!/usr/bin/env bash
set -e
echo "=== TASK-229: is_absolute_url https Fix ==="
[ -f "src/url_checker.py" ] || { echo "FAIL: url_checker.py not found"; exit 1; }
python -m pytest tests/test_url_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_absolute_url() accepts both http and https." || echo "FAIL"
exit $TEST_EXIT
