#!/usr/bin/env bash
set -e
echo "=== TASK-228: normalize_path Double Slash Fix ==="
[ -f "src/path_normalizer.py" ] || { echo "FAIL: path_normalizer.py not found"; exit 1; }
python -m pytest tests/test_path_normalizer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: normalize_path() no double slash." || echo "FAIL"
exit $TEST_EXIT
