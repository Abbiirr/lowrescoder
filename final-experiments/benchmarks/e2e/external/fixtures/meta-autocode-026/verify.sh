#!/usr/bin/env bash
set -e
echo "=== TASK-026: Release Semver Sort Fix ==="
echo "Pattern: go-gitea/gitea release tag sorting"
echo ""
[ -f "src/release_sorter.py" ] || { echo "FAIL: release_sorter.py not found"; exit 1; }
python -m pytest tests/test_release_sorter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: sort_releases() uses semver ordering." || echo "FAIL"
exit $TEST_EXIT
