#!/usr/bin/env bash
set -e
echo "=== TASK-138: Task Priority Selection Fix ==="
[ -f "src/task_priority.py" ] || { echo "FAIL: task_priority.py not found"; exit 1; }
python -m pytest tests/test_task_priority.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_next_task() returns lowest priority number." || echo "FAIL"
exit $TEST_EXIT
