#!/usr/bin/env bash
set -e
echo "=== TASK-073: Gitea Label Color Hex Validation Fix ==="
[ -f "src/color_validator.py" ] || { echo "FAIL: color_validator.py not found"; exit 1; }
python -m pytest tests/test_color_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_valid_label_color() validates #RRGGBB hex format." || echo "FAIL"
exit $TEST_EXIT
