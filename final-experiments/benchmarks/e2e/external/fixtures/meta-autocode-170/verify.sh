#!/usr/bin/env bash
set -e
echo "=== TASK-170: Pre-Release Version Detection Fix ==="
[ -f "src/version_checker.py" ] || { echo "FAIL: version_checker.py not found"; exit 1; }
python -m pytest tests/test_version_checker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_prerelease() detects '-' pre-release marker." || echo "FAIL"
exit $TEST_EXIT
