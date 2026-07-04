#!/usr/bin/env bash
set -e
echo "=== TASK-046: Gitea Path Traversal Guard Fix ==="
[ -f "src/path_guard.py" ] || { echo "FAIL: path_guard.py not found"; exit 1; }
python -m pytest tests/test_path_guard.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_safe_path() checks components not substrings." || echo "FAIL"
exit $TEST_EXIT
