#!/usr/bin/env bash
set -e
echo "=== TASK-198: Bare Import Classifier Fix ==="
[ -f "src/import_classifier.py" ] || { echo "FAIL: import_classifier.py not found"; exit 1; }
python -m pytest tests/test_import_classifier.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: is_bare_import() correctly rejects '../' relative paths." || echo "FAIL"
exit $TEST_EXIT
