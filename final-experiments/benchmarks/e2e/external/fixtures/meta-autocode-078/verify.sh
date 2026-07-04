#!/usr/bin/env bash
set -e
echo "=== TASK-078: Gitea Team Permission Level Hierarchy Fix ==="
[ -f "src/permission_checker.py" ] || { echo "FAIL: permission_checker.py not found"; exit 1; }
python -m pytest tests/test_permission_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: user_has_permission() uses >= for hierarchical levels." || echo "FAIL"
exit $TEST_EXIT
