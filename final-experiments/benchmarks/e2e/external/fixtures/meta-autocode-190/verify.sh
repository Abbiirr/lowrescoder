#!/usr/bin/env bash
set -e
echo "=== TASK-190: Branch Name Extraction Fix ==="
[ -f "src/ref_parser.py" ] || { echo "FAIL: ref_parser.py not found"; exit 1; }
python -m pytest tests/test_ref_parser.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: branch_from_ref() returns full nested branch name." || echo "FAIL"
exit $TEST_EXIT
