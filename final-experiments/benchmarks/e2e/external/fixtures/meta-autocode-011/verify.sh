#!/usr/bin/env bash
set -e
echo "=== TASK-011: Semver String Comparison Fix ==="
echo "Pattern: vitejs/vite version checks (harness-bench v2)"
echo ""
[ -f "src/semver.py" ] || { echo "FAIL: semver.py not found"; exit 1; }
python -m pytest tests/test_semver.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: Version comparison uses numeric tuples." || echo "FAIL"
exit $TEST_EXIT
