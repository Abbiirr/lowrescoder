#!/usr/bin/env bash
set -e
echo "=== TASK-104: gitea Commit Linter Type Check Inverted Fix ==="
[ -f "src/commit_linter.py" ] || { echo "FAIL: commit_linter.py not found"; exit 1; }
python -m pytest tests/test_commit_linter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: lint_commit_message() errors on unknown types only." || echo "FAIL"
exit $TEST_EXIT
