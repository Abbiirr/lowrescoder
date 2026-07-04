#!/usr/bin/env bash
set -e
echo "=== TASK-075: axios URL Param List Encoding Fix ==="
[ -f "src/param_encoder.py" ] || { echo "FAIL: param_encoder.py not found"; exit 1; }
python -m pytest tests/test_param_encoder.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: encode_params() repeats keys for list values." || echo "FAIL"
exit $TEST_EXIT
