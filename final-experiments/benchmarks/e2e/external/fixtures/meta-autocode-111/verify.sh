#!/usr/bin/env bash
set -e
echo "=== TASK-111: gitea Page Count Ceiling Division Fix ==="
[ -f "src/page_calculator.py" ] || { echo "FAIL: page_calculator.py not found"; exit 1; }
python -m pytest tests/test_page_calculator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_page_count() uses ceiling division." || echo "FAIL"
exit $TEST_EXIT
