#!/usr/bin/env bash
set -e
echo "=== TASK-021: Terminal Display Width Tab Expansion Fix ==="
echo "Pattern: sharkdp/bat tab-stop width calculation"
echo ""
[ -f "src/display_width.py" ] || { echo "FAIL: display_width.py not found"; exit 1; }
python -m pytest tests/test_display_width.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: display_width() expands tabs to tab stops." || echo "FAIL"
exit $TEST_EXIT
