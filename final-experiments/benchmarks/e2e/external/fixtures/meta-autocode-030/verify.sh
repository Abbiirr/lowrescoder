#!/usr/bin/env bash
set -e
echo "=== TASK-030: FastAPI Path Param Negative Int Fix ==="
echo "Pattern: fastapi/fastapi path parameter type coercion"
echo ""
[ -f "src/path_param.py" ] || { echo "FAIL: path_param.py not found"; exit 1; }
python -m pytest tests/test_path_param.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: parse_path_param() handles negative integers." || echo "FAIL"
exit $TEST_EXIT
