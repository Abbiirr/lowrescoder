#!/usr/bin/env bash
set -e
echo "=== TASK-088: gitea Issue Reference Extractor Keywords Fix ==="
[ -f "src/issue_linker.py" ] || { echo "FAIL: issue_linker.py not found"; exit 1; }
python -m pytest tests/test_issue_linker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: extract_issue_refs() matches all closing keywords." || echo "FAIL"
exit $TEST_EXIT
