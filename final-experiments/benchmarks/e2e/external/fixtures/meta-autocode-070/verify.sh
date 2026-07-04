#!/usr/bin/env bash
set -e
echo "=== TASK-070: Gitea PR Closing Issue Detection Case Fix ==="
[ -f "src/pr_issue_finder.py" ] || { echo "FAIL: pr_issue_finder.py not found"; exit 1; }
python -m pytest tests/test_pr_issue_finder.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: find_closing_issues() is case-insensitive." || echo "FAIL"
exit $TEST_EXIT
