#!/usr/bin/env bash
set -e
echo "=== TASK-132: Git Log Parser Split Count Fix ==="
[ -f "src/git_log_parser.py" ] || { echo "FAIL: git_log_parser.py not found"; exit 1; }
python -m pytest tests/test_git_log_parser.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: parse_commit_line() correctly splits hash|author|message." || echo "FAIL"
exit $TEST_EXIT
