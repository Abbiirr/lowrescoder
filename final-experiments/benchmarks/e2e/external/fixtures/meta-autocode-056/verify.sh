#!/usr/bin/env bash
set -e
echo "=== TASK-056: Vite Plugin Enforce Ordering Fix ==="
[ -f "src/plugin_sorter.py" ] || { echo "FAIL: plugin_sorter.py not found"; exit 1; }
python -m pytest tests/test_plugin_sorter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: sort_plugins() respects enforce order (pre→normal→post)." || echo "FAIL"
exit $TEST_EXIT
