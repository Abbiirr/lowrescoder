#!/usr/bin/env bash
set -e
echo "=== TASK-150: File Extension Extraction Fix ==="
[ -f "src/asset_resolver.py" ] || { echo "FAIL: asset_resolver.py not found"; exit 1; }
python -m pytest tests/test_asset_resolver.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_extension() returns '' for no-extension files." || echo "FAIL"
exit $TEST_EXIT
