#!/usr/bin/env bash
set -e
echo "=== TASK-085: vite Config Getter None vs Missing Fix ==="
[ -f "src/config_getter.py" ] || { echo "FAIL: config_getter.py not found"; exit 1; }
python -m pytest tests/test_config_getter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_nested() distinguishes None from missing." || echo "FAIL"
exit $TEST_EXIT
