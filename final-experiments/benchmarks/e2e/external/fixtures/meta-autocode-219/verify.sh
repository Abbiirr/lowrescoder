#!/usr/bin/env bash
set -e
echo "=== TASK-219: is_body_too_large Boundary Fix ==="
[ -f "src/body_size.py" ] || { echo "FAIL: body_size.py not found"; exit 1; }
python -m pytest tests/test_body_size.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_body_too_large() uses strict greater-than." || echo "FAIL"
exit $TEST_EXIT
