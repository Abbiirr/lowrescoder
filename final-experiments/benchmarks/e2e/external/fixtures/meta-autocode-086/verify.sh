#!/usr/bin/env bash
set -e
echo "=== TASK-086: axios Request Header Merger Content-Type Fix ==="
[ -f "src/request_merger.py" ] || { echo "FAIL: request_merger.py not found"; exit 1; }
python -m pytest tests/test_request_merger.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: merge_request_headers() uses setdefault for Content-Type." || echo "FAIL"
exit $TEST_EXIT
