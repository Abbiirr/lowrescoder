#!/usr/bin/env bash
set -e
echo "=== TASK-124: Plugin Registry Case-Insensitive Fix ==="
[ -f "src/plugin_registry.py" ] || { echo "FAIL: plugin_registry.py not found"; exit 1; }
python -m pytest tests/test_plugin_registry.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_plugin() performs case-insensitive lookup." || echo "FAIL"
exit $TEST_EXIT
