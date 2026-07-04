#!/usr/bin/env bash
set -e
echo "=== TASK-116: langflow Batch Processor Off-By-One Slice Fix ==="
[ -f "src/batch_processor.py" ] || { echo "FAIL: batch_processor.py not found"; exit 1; }
python -m pytest tests/test_batch_processor.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: process_in_batches() uses correct slice end." || echo "FAIL"
exit $TEST_EXIT
