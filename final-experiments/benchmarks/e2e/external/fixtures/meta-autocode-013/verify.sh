#!/usr/bin/env bash
set -e
echo "=== TASK-013: Commit Counter Assignment Bug Fix ==="
echo "Pattern: go-gitea/gitea contributor stats (harness-bench v2)"
echo ""
[ -f "src/commit_stats.py" ] || { echo "FAIL: commit_stats.py not found"; exit 1; }
python -m pytest tests/test_commit_stats.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: Commit counts accumulate correctly." || echo "FAIL"
exit $TEST_EXIT
