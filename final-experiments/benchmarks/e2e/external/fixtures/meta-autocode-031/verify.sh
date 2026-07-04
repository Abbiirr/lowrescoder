#!/usr/bin/env bash
set -e
echo "=== TASK-031: axios Request Header Merge Fix ==="
echo "Pattern: axios/axios default + config header merging"
echo ""
[ -f "src/header_merger.py" ] || { echo "FAIL: header_merger.py not found"; exit 1; }
python -m pytest tests/test_header_merger.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: merge_request_headers() merges defaults with config." || echo "FAIL"
exit $TEST_EXIT
