#!/usr/bin/env bash
set -e
echo "=== TASK-180: JS File Extension Check Fix ==="
[ -f "src/module_checker.py" ] || { echo "FAIL: module_checker.py not found"; exit 1; }
python -m pytest tests/test_module_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_js_file() recognises .js, .mjs, and .cjs." || echo "FAIL"
exit $TEST_EXIT
