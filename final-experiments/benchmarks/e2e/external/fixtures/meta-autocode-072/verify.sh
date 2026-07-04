#!/usr/bin/env bash
set -e
echo "=== TASK-072: langflow Component Description Validation Fix ==="
[ -f "src/component_validator.py" ] || { echo "FAIL: component_validator.py not found"; exit 1; }
python -m pytest tests/test_component_validator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: validate_component_metadata() checks both name and description." || echo "FAIL"
exit $TEST_EXIT
