#!/usr/bin/env bash
set -e
echo "=== TASK-117: gitea Clone URL Builder HTTPS vs SSH Fix ==="
[ -f "src/repo_cloner.py" ] || { echo "FAIL: repo_cloner.py not found"; exit 1; }
python -m pytest tests/test_repo_cloner.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: build_clone_url() uses https:// for HTTPS protocol." || echo "FAIL"
exit $TEST_EXIT
