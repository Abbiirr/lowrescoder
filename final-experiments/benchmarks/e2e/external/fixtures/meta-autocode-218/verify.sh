#!/usr/bin/env bash
set -e
echo "=== TASK-218: is_valid_component_id Underscore Fix ==="
[ -f "src/component_id.py" ] || { echo "FAIL: component_id.py not found"; exit 1; }
python -m pytest tests/test_component_id.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_valid_component_id() accepts underscores." || echo "FAIL"
exit $TEST_EXIT
