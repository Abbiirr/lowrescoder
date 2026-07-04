#!/usr/bin/env bash
set -e
echo "=== TASK-083: lazygit Argument Joiner Separator Fix ==="
[ -f "src/arg_builder.py" ] || { echo "FAIL: arg_builder.py not found"; exit 1; }
python -m pytest tests/test_arg_builder.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: build_git_args() joins with space." || echo "FAIL"
exit $TEST_EXIT
