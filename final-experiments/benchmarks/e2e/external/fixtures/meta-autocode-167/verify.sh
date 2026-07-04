#!/usr/bin/env bash
set -e
echo "=== TASK-167: Deduplication seen.add Fix ==="
[ -f "src/list_dedup.py" ] || { echo "FAIL: list_dedup.py not found"; exit 1; }
python -m pytest tests/test_list_dedup.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: deduplicate() correctly removes duplicates." || echo "FAIL"
exit $TEST_EXIT
