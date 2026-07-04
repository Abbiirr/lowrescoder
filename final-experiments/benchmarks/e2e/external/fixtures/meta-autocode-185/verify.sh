#!/usr/bin/env bash
set -e
echo "=== TASK-185: Repo Name Slash Check Fix ==="
[ -f "src/repo_validator.py" ] || { echo "FAIL: repo_validator.py not found"; exit 1; }
python -m pytest tests/test_repo_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_valid_repo_name() rejects names with slashes." || echo "FAIL"
exit $TEST_EXIT
