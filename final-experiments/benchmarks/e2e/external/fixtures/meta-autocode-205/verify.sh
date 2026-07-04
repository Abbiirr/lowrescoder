#!/usr/bin/env bash
set -e
echo "=== TASK-205: Page Count Fix ==="
[ -f "src/paginator.py" ] || { echo "FAIL: paginator.py not found"; exit 1; }
python -m pytest tests/test_paginator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: page_count() rounds up for partial last page." || echo "FAIL"
exit $TEST_EXIT
