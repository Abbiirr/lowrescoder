#!/usr/bin/env bash
set -e
echo "=== TASK-173: ASCII Printable Check Fix ==="
[ -f "src/char_validator.py" ] || { echo "FAIL: char_validator.py not found"; exit 1; }
python -m pytest tests/test_char_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_printable_ascii() rejects control characters." || echo "FAIL"
exit $TEST_EXIT
