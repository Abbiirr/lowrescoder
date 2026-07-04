#!/usr/bin/env bash
set -e
echo "=== TASK-168: Access Control and/or Fix ==="
[ -f "src/access_control.py" ] || { echo "FAIL: access_control.py not found"; exit 1; }
python -m pytest tests/test_access_control.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: can_edit_memo() allows owner OR admin." || echo "FAIL"
exit $TEST_EXIT
