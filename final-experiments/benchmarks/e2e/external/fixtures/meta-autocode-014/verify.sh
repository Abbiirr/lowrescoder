#!/usr/bin/env bash
set -e
echo "=== TASK-014: Display Truncation Suffix Overflow Fix ==="
echo "Pattern: jesseduffield/lazygit terminal rendering (harness-bench v2)"
echo ""
[ -f "src/display.py" ] || { echo "FAIL: display.py not found"; exit 1; }
python -m pytest tests/test_display.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: truncate() respects max_len including suffix." || echo "FAIL"
exit $TEST_EXIT
