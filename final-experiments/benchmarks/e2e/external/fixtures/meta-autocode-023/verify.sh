#!/usr/bin/env bash
set -e
echo "=== TASK-023: Vite Config Merger Array Concatenation Fix ==="
echo "Pattern: vitejs/vite mergeConfig array handling"
echo ""
[ -f "src/config_merger.py" ] || { echo "FAIL: config_merger.py not found"; exit 1; }
python -m pytest tests/test_config_merger.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: merge_vite_config() concatenates arrays." || echo "FAIL"
exit $TEST_EXIT
