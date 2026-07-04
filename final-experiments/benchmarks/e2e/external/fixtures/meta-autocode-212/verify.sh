#!/usr/bin/env bash
set -e
echo "=== TASK-212: count_open_issues State Filter Fix ==="
[ -f "src/issue_counter.py" ] || { echo "FAIL: issue_counter.py not found"; exit 1; }
python -m pytest tests/test_issue_counter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: count_open_issues() filters by state." || echo "FAIL"
exit $TEST_EXIT
