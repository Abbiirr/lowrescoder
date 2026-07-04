#!/usr/bin/env bash
set -e
echo "=== TASK-098: bat File Size Formatter Binary Units Fix ==="
[ -f "src/file_sizer.py" ] || { echo "FAIL: file_sizer.py not found"; exit 1; }
python -m pytest tests/test_file_sizer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: format_file_size() uses 1024 binary units." || echo "FAIL"
exit $TEST_EXIT
