#!/usr/bin/env bash
set -e
echo "=== TASK-141: Repository Fork Count Increment Fix ==="
[ -f "src/repo_forker.py" ] || { echo "FAIL: repo_forker.py not found"; exit 1; }
python -m pytest tests/test_repo_forker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: fork_repository() increments fork_count." || echo "FAIL"
exit $TEST_EXIT
