#!/usr/bin/env bash
set -e
echo "=== TASK-067: bat CR Line Ending Normalization Fix ==="
[ -f "src/line_normalizer.py" ] || { echo "FAIL: line_normalizer.py not found"; exit 1; }
python -m pytest tests/test_line_normalizer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: normalize_line_endings() handles both \\r\\n and standalone \\r." || echo "FAIL"
exit $TEST_EXIT
