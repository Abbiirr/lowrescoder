#!/usr/bin/env bash
set -e
echo "=== TASK-241: split_into_chunks Range Fix ==="
[ -f "src/text_chunker.py" ] || { echo "FAIL: text_chunker.py not found"; exit 1; }
python -m pytest tests/test_text_chunker.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: split_into_chunks() includes all chunks." || echo "FAIL"
exit $TEST_EXIT
