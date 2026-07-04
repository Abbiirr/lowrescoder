#!/usr/bin/env bash
set -e
echo "=== TASK-235: get_stash_count Key Fix ==="
[ -f "src/stash_info.py" ] || { echo "FAIL: stash_info.py not found"; exit 1; }
python -m pytest tests/test_stash_info.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_stash_count() reads 'entries'." || echo "FAIL"
exit $TEST_EXIT
