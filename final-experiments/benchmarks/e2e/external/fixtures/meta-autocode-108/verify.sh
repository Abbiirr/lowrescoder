#!/usr/bin/env bash
set -e
echo "=== TASK-108: vite File Watcher Extension Dot Normalization Fix ==="
[ -f "src/file_watcher.py" ] || { echo "FAIL: file_watcher.py not found"; exit 1; }
python -m pytest tests/test_file_watcher.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: get_watched_extensions() strips leading dot." || echo "FAIL"
exit $TEST_EXIT
