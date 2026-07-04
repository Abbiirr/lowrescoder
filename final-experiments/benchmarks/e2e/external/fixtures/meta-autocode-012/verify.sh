#!/usr/bin/env bash
set -e
echo "=== TASK-012: File Extension Detection Fix ==="
echo "Pattern: sharkdp/bat file-type detection (harness-bench v2)"
echo ""
[ -f "src/file_detector.py" ] || { echo "FAIL: file_detector.py not found"; exit 1; }
python -m pytest tests/test_file_detector.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: Multi-dot filenames return correct language." || echo "FAIL"
exit $TEST_EXIT
