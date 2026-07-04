#!/usr/bin/env bash
set -e
echo "=== TASK-163: Missing Return True Fix ==="
[ -f "src/collection_utils.py" ] || { echo "FAIL: collection_utils.py not found"; exit 1; }
python -m pytest tests/test_collection_utils.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: all_unique() returns True for unique lists." || echo "FAIL"
exit $TEST_EXIT
