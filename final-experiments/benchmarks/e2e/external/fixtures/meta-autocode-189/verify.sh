#!/usr/bin/env bash
set -e
echo "=== TASK-189: Extension Removal Fix ==="
[ -f "src/path_utils.py" ] || { echo "FAIL: path_utils.py not found"; exit 1; }
python -m pytest tests/test_path_utils.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: remove_extension() removes only the last dot segment." || echo "FAIL"
exit $TEST_EXIT
