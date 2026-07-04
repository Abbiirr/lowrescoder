#!/usr/bin/env bash
set -e
echo "=== TASK-230: count_watchers Key Fix ==="
[ -f "src/watcher_counter.py" ] || { echo "FAIL: watcher_counter.py not found"; exit 1; }
python -m pytest tests/test_watcher_counter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: count_watchers() reads watchers_count." || echo "FAIL"
exit $TEST_EXIT
