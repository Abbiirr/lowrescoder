#!/usr/bin/env bash
set -e
echo "=== TASK-234: is_dev_mode Key Fix ==="
[ -f "src/build_mode.py" ] || { echo "FAIL: build_mode.py not found"; exit 1; }
python -m pytest tests/test_build_mode.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_dev_mode() reads 'mode' key." || echo "FAIL"
exit $TEST_EXIT
