#!/usr/bin/env bash
set -e
echo "=== TASK-100: langflow Priority Queue Min vs Max Fix ==="
[ -f "src/priority_queue.py" ] || { echo "FAIL: priority_queue.py not found"; exit 1; }
python -m pytest tests/test_priority_queue.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_highest_priority() uses max()." || echo "FAIL"
exit $TEST_EXIT
