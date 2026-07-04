#!/usr/bin/env bash
set -e
echo "=== TASK-137: Search Indexer Overwrite Fix ==="
[ -f "src/search_indexer.py" ] || { echo "FAIL: search_indexer.py not found"; exit 1; }
python -m pytest tests/test_search_indexer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: build_index() accumulates doc_ids per word." || echo "FAIL"
exit $TEST_EXIT
