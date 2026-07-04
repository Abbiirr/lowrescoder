#!/usr/bin/env bash
set -e
echo "=== TASK-127: Response Timer Subtraction Order Fix ==="
[ -f "src/response_timer.py" ] || { echo "FAIL: response_timer.py not found"; exit 1; }
python -m pytest tests/test_response_timer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: compute_elapsed_ms() returns positive elapsed time." || echo "FAIL"
exit $TEST_EXIT
