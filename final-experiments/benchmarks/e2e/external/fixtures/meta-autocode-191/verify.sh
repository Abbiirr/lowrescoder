#!/usr/bin/env bash
set -e
echo "=== TASK-191: Left Pad Character Fix ==="
[ -f "src/string_formatter.py" ] || { echo "FAIL: string_formatter.py not found"; exit 1; }
python -m pytest tests/test_string_formatter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: left_pad() uses the specified pad character." || echo "FAIL"
exit $TEST_EXIT
