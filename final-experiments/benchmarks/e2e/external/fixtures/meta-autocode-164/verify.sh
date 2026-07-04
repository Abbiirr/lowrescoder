#!/usr/bin/env bash
set -e
echo "=== TASK-164: Top Contributors Sort Fix ==="
[ -f "src/repo_stats.py" ] || { echo "FAIL: repo_stats.py not found"; exit 1; }
python -m pytest tests/test_repo_stats.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_top_contributors() returns highest-count authors." || echo "FAIL"
exit $TEST_EXIT
