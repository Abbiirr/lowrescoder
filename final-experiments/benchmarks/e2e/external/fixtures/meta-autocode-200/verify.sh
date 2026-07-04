#!/usr/bin/env bash
set -e
echo "=== TASK-200: Overlapping Keys Fix ==="
[ -f "src/dict_utils.py" ] || { echo "FAIL: dict_utils.py not found"; exit 1; }
python -m pytest tests/test_dict_utils.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: have_overlapping_keys() detects partial key overlap." || echo "FAIL"
exit $TEST_EXIT
