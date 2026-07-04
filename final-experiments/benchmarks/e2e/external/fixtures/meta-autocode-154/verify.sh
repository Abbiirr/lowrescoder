#!/usr/bin/env bash
set -e
echo "=== TASK-154: Git Tag Ref Detection Fix ==="
[ -f "src/ref_checker.py" ] || { echo "FAIL: ref_checker.py not found"; exit 1; }
python -m pytest tests/test_ref_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_tag_ref() correctly identifies refs/tags/ references." || echo "FAIL"
exit $TEST_EXIT
