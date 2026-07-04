#!/usr/bin/env bash
set -e
echo "=== TASK-121: Cache Invalidator Multi-Tag Fix ==="
[ -f "src/cache_invalidator.py" ] || { echo "FAIL: cache_invalidator.py not found"; exit 1; }
python -m pytest tests/test_cache_invalidator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: invalidate_keys() removes all tagged entries." || echo "FAIL"
exit $TEST_EXIT
