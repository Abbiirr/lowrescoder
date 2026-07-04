#!/usr/bin/env bash
set -e
echo "=== TASK-146: Tag Merger Union Fix ==="
[ -f "src/tag_merger.py" ] || { echo "FAIL: tag_merger.py not found"; exit 1; }
python -m pytest tests/test_tag_merger.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: merge_tag_sets() returns union not intersection." || echo "FAIL"
exit $TEST_EXIT
