#!/usr/bin/env bash
set -e
echo "=== TASK-248: get_repo_language Wrong Key Fix ==="
[ -f "src/repo_language.py" ] || { echo "FAIL: repo_language.py not found"; exit 1; }
python -m pytest tests/test_repo_language.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_repo_language() reads 'language' key." || echo "FAIL"
exit $TEST_EXIT
