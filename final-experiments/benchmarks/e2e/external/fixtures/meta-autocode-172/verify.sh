#!/usr/bin/env bash
set -e
echo "=== TASK-172: camelCase to snake_case Fix ==="
[ -f "src/case_converter.py" ] || { echo "FAIL: case_converter.py not found"; exit 1; }
python -m pytest tests/test_case_converter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: camel_to_snake() handles PascalCase without leading underscore." || echo "FAIL"
exit $TEST_EXIT
