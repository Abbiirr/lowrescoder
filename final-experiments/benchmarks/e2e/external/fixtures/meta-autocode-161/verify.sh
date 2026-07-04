#!/usr/bin/env bash
set -e
echo "=== TASK-161: Mode Finder min/max Fix ==="
[ -f "src/stats_utils.py" ] || { echo "FAIL: stats_utils.py not found"; exit 1; }
python -m pytest tests/test_stats_utils.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: find_mode() returns most frequent item." || echo "FAIL"
exit $TEST_EXIT
