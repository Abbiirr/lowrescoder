#!/usr/bin/env bash
set -e
echo "=== TASK-038: Gitea Pagination Total Count Fix ==="
echo "Pattern: go-gitea/gitea REST API pagination total"
echo ""
[ -f "src/paginator.py" ] || { echo "FAIL: paginator.py not found"; exit 1; }
python -m pytest tests/test_paginator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: paginate() total reflects full collection size." || echo "FAIL"
exit $TEST_EXIT
