#!/usr/bin/env bash
set -e
echo "=== TASK-152: Event Log Recent-N Fix ==="
[ -f "src/event_log.py" ] || { echo "FAIL: event_log.py not found"; exit 1; }
python -m pytest tests/test_event_log.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_recent_events() returns last N items." || echo "FAIL"
exit $TEST_EXIT
