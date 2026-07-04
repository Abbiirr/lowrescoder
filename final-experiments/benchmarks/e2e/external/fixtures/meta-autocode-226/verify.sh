#!/usr/bin/env bash
set -e
echo "=== TASK-226: abbreviate_branch Ellipsis Fix ==="
[ -f "src/branch_abbreviator.py" ] || { echo "FAIL: branch_abbreviator.py not found"; exit 1; }
python -m pytest tests/test_branch_abbreviator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: abbreviate_branch() adds ellipsis." || echo "FAIL"
exit $TEST_EXIT
