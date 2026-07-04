#!/usr/bin/env bash
set -e
echo "=== TASK-110: langflow Lazy Loader Always Calls Loader Fix ==="
[ -f "src/lazy_loader.py" ] || { echo "FAIL: lazy_loader.py not found"; exit 1; }
python -m pytest tests/test_lazy_loader.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_or_load() uses cache after first call." || echo "FAIL"
exit $TEST_EXIT
