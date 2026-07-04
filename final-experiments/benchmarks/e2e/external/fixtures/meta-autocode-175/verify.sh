#!/usr/bin/env bash
set -e
echo "=== TASK-175: HTTPS URL Check Fix ==="
[ -f "src/url_utils.py" ] || { echo "FAIL: url_utils.py not found"; exit 1; }
python -m pytest tests/test_url_utils.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_secure_url() requires 'https://' prefix." || echo "FAIL"
exit $TEST_EXIT
