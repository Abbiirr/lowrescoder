#!/usr/bin/env bash
set -e
echo "=== TASK-216: has_hot_reload Config Key Fix ==="
[ -f "src/hmr_checker.py" ] || { echo "FAIL: hmr_checker.py not found"; exit 1; }
python -m pytest tests/test_hmr_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: has_hot_reload() reads correct key." || echo "FAIL"
exit $TEST_EXIT
