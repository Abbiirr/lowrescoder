#!/usr/bin/env bash
set -e
echo "=== TASK-194: Admin Role Check Fix ==="
[ -f "src/role_checker.py" ] || { echo "FAIL: role_checker.py not found"; exit 1; }
python -m pytest tests/test_role_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_admin() accepts both admin and owner roles." || echo "FAIL"
exit $TEST_EXIT
