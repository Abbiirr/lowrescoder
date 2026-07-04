#!/usr/bin/env bash
set -e
echo "=== TASK-142: String Truncator Max Length Fix ==="
[ -f "src/string_truncator.py" ] || { echo "FAIL: string_truncator.py not found"; exit 1; }
python -m pytest tests/test_string_truncator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: truncate() result never exceeds max_length." || echo "FAIL"
exit $TEST_EXIT
