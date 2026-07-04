#!/usr/bin/env bash
set -e
echo "=== TASK-114: gitea Event Deduplicator Composite Key Fix ==="
[ -f "src/event_deduplicator.py" ] || { echo "FAIL: event_deduplicator.py not found"; exit 1; }
python -m pytest tests/test_event_deduplicator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: deduplicate_events() uses (type, resource_id) as key." || echo "FAIL"
exit $TEST_EXIT
