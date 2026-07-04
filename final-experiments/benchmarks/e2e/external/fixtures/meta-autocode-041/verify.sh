#!/usr/bin/env bash
set -e
echo "=== TASK-041: bat Theme List Case-Insensitive Sort Fix ==="
echo "Pattern: sharkdp/bat --list-themes alphabetical order"
echo ""
[ -f "src/theme_sorter.py" ] || { echo "FAIL: theme_sorter.py not found"; exit 1; }
python -m pytest tests/test_theme_sorter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: list_themes() sorts case-insensitively." || echo "FAIL"
exit $TEST_EXIT
