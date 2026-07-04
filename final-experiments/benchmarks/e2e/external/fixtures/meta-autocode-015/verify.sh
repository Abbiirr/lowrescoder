#!/usr/bin/env bash
set -e
echo "=== TASK-015: Config Deep Merge Fix ==="
echo "Pattern: vitejs/vite config merging (harness-bench v2)"
echo ""
[ -f "src/config_merger.py" ] || { echo "FAIL: config_merger.py not found"; exit 1; }
python -m pytest tests/test_config_merger.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: merge_config() recursively merges nested dicts." || echo "FAIL"
exit $TEST_EXIT
