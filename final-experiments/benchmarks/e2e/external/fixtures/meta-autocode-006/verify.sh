#!/usr/bin/env bash
set -e
echo "=== TASK-006: Pydantic Color Encoder Fix ==="
echo "Pattern: fastapi/fastapi PR#15101 (harness-bench v2)"
echo ""
[ -f "src/color_encoder.py" ] || { echo "FAIL: color_encoder.py not found"; exit 1; }
python -m pytest tests/test_color_encoder.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: Color encoder handles both legacy and modern Pydantic." || echo "FAIL"
exit $TEST_EXIT
