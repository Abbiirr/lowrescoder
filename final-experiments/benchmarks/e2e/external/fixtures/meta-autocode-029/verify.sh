#!/usr/bin/env bash
set -e
echo "=== TASK-029: lazygit Branch Name Dot Validation Fix ==="
echo "Pattern: jesseduffield/lazygit branch name validator"
echo ""
[ -f "src/branch_validator.py" ] || { echo "FAIL: branch_validator.py not found"; exit 1; }
python -m pytest tests/test_branch_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_valid_branch_name() handles single dots correctly." || echo "FAIL"
exit $TEST_EXIT
