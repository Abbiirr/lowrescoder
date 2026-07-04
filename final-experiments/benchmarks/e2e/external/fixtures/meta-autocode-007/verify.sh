#!/usr/bin/env bash
set -e
echo "=== TASK-007: Pagination Off-by-One Fix ==="
echo "Pattern: memos/gitea pagination (harness-bench v2)"
echo ""
[ -f "src/paginator.py" ] || { echo "FAIL: paginator.py not found"; exit 1; }
python -m pytest tests/test_paginator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: Pagination returns correct pages." || echo "FAIL"
exit $TEST_EXIT
