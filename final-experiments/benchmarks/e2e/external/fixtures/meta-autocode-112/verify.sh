#!/usr/bin/env bash
set -e
echo "=== TASK-112: vite Port Availability Check Inverted Fix ==="
[ -f "src/port_allocator.py" ] || { echo "FAIL: port_allocator.py not found"; exit 1; }
python -m pytest tests/test_port_allocator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_port_available() returns True when port is free." || echo "FAIL"
exit $TEST_EXIT
