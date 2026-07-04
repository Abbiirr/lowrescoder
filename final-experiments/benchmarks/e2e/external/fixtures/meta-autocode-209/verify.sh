#!/usr/bin/env bash
set -e
echo "=== TASK-209: merge_unique Deduplication Fix ==="
[ -f "src/list_merger.py" ] || { echo "FAIL: list_merger.py not found"; exit 1; }
python -m pytest tests/test_list_merger.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: merge_unique() removes duplicates." || echo "FAIL"
exit $TEST_EXIT
