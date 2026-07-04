#!/usr/bin/env bash
set -e
echo "=== TASK-136: Tag Sorter Count Descending Fix ==="
[ -f "src/tag_sorter.py" ] || { echo "FAIL: tag_sorter.py not found"; exit 1; }
python -m pytest tests/test_tag_sorter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: sort_tags(by='count') returns descending order." || echo "FAIL"
exit $TEST_EXIT
