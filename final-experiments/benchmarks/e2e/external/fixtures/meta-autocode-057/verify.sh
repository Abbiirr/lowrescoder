#!/usr/bin/env bash
set -e
echo "=== TASK-057: langflow Duplicate Output Port Detection Fix ==="
[ -f "src/port_validator.py" ] || { echo "FAIL: port_validator.py not found"; exit 1; }
python -m pytest tests/test_port_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: validate_output_ports() catches duplicate names." || echo "FAIL"
exit $TEST_EXIT
