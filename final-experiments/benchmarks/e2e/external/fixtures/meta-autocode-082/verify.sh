#!/usr/bin/env bash
set -e
echo "=== TASK-082: gitea Repository Unstar Counter Fix ==="
[ -f "src/repo_star_counter.py" ] || { echo "FAIL: repo_star_counter.py not found"; exit 1; }
python -m pytest tests/test_repo_star_counter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: toggle_star() decrements on unstar." || echo "FAIL"
exit $TEST_EXIT
