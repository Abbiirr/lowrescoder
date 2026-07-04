#!/usr/bin/env bash
set -e
echo "=== TASK-048: Gitea Repository Fork Count Fix ==="
[ -f "src/fork_counter.py" ] || { echo "FAIL: fork_counter.py not found"; exit 1; }
python -m pytest tests/test_fork_counter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: fork_repository() increments fork_count." || echo "FAIL"
exit $TEST_EXIT
