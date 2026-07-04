#!/usr/bin/env bash
set -e
echo "=== TASK-158: Relative Path Detection Fix ==="
[ -f "src/module_resolver.py" ] || { echo "FAIL: module_resolver.py not found"; exit 1; }
python -m pytest tests/test_module_resolver.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_relative_path() handles both ./ and ../ paths." || echo "FAIL"
exit $TEST_EXIT
