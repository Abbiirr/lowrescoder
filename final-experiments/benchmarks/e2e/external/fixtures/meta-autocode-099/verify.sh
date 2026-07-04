#!/usr/bin/env bash
set -e
echo "=== TASK-099: vite Config Merger Base Mutation Fix ==="
[ -f "src/config_merger.py" ] || { echo "FAIL: config_merger.py not found"; exit 1; }
python -m pytest tests/test_config_merger.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: merge_configs() does not mutate base config." || echo "FAIL"
exit $TEST_EXIT
