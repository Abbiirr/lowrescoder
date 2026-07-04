#!/usr/bin/env bash
set -e
echo "=== TASK-093: gitea PR Merge Check Key Name Fix ==="
[ -f "src/pr_merger.py" ] || { echo "FAIL: pr_merger.py not found"; exit 1; }
python -m pytest tests/test_pr_merger.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: can_merge_pr() checks review_approved key." || echo "FAIL"
exit $TEST_EXIT
