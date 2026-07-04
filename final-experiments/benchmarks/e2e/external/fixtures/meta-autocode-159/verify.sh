#!/usr/bin/env bash
set -e
echo "=== TASK-159: Date Range Overlap Fix ==="
[ -f "src/date_range.py" ] || { echo "FAIL: date_range.py not found"; exit 1; }
python -m pytest tests/test_date_range.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: ranges_overlap() handles all overlap cases." || echo "FAIL"
exit $TEST_EXIT
