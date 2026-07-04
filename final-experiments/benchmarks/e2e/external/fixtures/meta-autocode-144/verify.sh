#!/usr/bin/env bash
set -e
echo "=== TASK-144: Paginator Offset Calculation Fix ==="
[ -f "src/paginator.py" ] || { echo "FAIL: paginator.py not found"; exit 1; }
python -m pytest tests/test_paginator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_page_items() uses (page-1)*page_size offset." || echo "FAIL"
exit $TEST_EXIT
