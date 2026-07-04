#!/usr/bin/env bash
set -e
echo "=== TASK-123: Event Scheduler Due Check Fix ==="
[ -f "src/event_scheduler.py" ] || { echo "FAIL: event_scheduler.py not found"; exit 1; }
python -m pytest tests/test_event_scheduler.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_due_events() returns events at or before current_time." || echo "FAIL"
exit $TEST_EXIT
