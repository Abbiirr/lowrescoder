#!/usr/bin/env bash
set -e
echo "=== TASK-043: lazygit Commit Date Zero-Padding Fix ==="
[ -f "src/date_formatter.py" ] || { echo "FAIL: date_formatter.py not found"; exit 1; }
python -m pytest tests/test_date_formatter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: format_commit_date() zero-pads month and day." || echo "FAIL"
exit $TEST_EXIT
