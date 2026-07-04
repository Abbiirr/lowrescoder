#!/usr/bin/env bash
set -e
echo "=== TASK-079: memos Memo Pin Toggle Fix ==="
[ -f "src/pin_toggler.py" ] || { echo "FAIL: pin_toggler.py not found"; exit 1; }
python -m pytest tests/test_pin_toggler.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: toggle_pin() toggles True→False and False→True." || echo "FAIL"
exit $TEST_EXIT
