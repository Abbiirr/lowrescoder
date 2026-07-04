#!/usr/bin/env bash
set -e
echo "=== TASK-061: Gitea Issue Comment Counter Fix ==="
[ -f "src/comment_counter.py" ] || { echo "FAIL: comment_counter.py not found"; exit 1; }
python -m pytest tests/test_comment_counter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: count_issue_comments() excludes replies." || echo "FAIL"
exit $TEST_EXIT
