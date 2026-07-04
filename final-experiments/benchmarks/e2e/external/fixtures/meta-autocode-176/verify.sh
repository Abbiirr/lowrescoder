#!/usr/bin/env bash
set -e
echo "=== TASK-176: Commit Message Whitespace Fix ==="
[ -f "src/commit_formatter.py" ] || { echo "FAIL: commit_formatter.py not found"; exit 1; }
python -m pytest tests/test_commit_formatter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: format_commit() strips whitespace from message." || echo "FAIL"
exit $TEST_EXIT
