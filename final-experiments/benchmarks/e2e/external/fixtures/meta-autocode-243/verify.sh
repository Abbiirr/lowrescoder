#!/usr/bin/env bash
set -e
echo "=== TASK-243: get_base_url Wrong Key Fix ==="
[ -f "src/base_url_reader.py" ] || { echo "FAIL: base_url_reader.py not found"; exit 1; }
python -m pytest tests/test_base_url_reader.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_base_url() reads 'base' key." || echo "FAIL"
exit $TEST_EXIT
