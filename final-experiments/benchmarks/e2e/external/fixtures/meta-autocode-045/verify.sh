#!/usr/bin/env bash
set -e
echo "=== TASK-045: langflow String-to-Bool Coercion Fix ==="
[ -f "src/bool_coercer.py" ] || { echo "FAIL: bool_coercer.py not found"; exit 1; }
python -m pytest tests/test_bool_coercer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: coerce_to_bool() handles string representations." || echo "FAIL"
exit $TEST_EXIT
