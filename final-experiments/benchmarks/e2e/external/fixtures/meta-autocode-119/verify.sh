#!/usr/bin/env bash
set -e
echo "=== TASK-119: Semantic Version Comparator Fix ==="
[ -f "src/semver_comparator.py" ] || { echo "FAIL: semver_comparator.py not found"; exit 1; }
python -m pytest tests/test_semver_comparator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: compare_versions() uses integer comparison." || echo "FAIL"
exit $TEST_EXIT
