#!/usr/bin/env bash
set -e
echo "=== TASK-051: Memos Content Truncation Ellipsis Fix ==="
[ -f "src/content_truncator.py" ] || { echo "FAIL: content_truncator.py not found"; exit 1; }
python -m pytest tests/test_content_truncator.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: truncate_content() appends '...' when truncating." || echo "FAIL"
exit $TEST_EXIT
