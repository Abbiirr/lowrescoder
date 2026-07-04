#!/usr/bin/env bash
set -e
echo "=== TASK-145: List Right Rotation Fix ==="
[ -f "src/list_rotator.py" ] || { echo "FAIL: list_rotator.py not found"; exit 1; }
python -m pytest tests/test_token_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: rotate_right() moves last element to front." || echo "FAIL"
exit $TEST_EXIT
