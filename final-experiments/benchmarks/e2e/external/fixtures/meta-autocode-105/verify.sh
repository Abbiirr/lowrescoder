#!/usr/bin/env bash
set -e
echo "=== TASK-105: gitea Watch Counter Field Update Fix ==="
[ -f "src/watch_counter.py" ] || { echo "FAIL: watch_counter.py not found"; exit 1; }
python -m pytest tests/test_watch_counter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: update_watch_count() stores count in repo['watch_count']." || echo "FAIL"
exit $TEST_EXIT
