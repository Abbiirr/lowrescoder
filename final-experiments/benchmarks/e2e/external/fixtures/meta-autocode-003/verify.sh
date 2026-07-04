#!/usr/bin/env bash
set -e

echo "=== meta-autocode TASK-003 Verification ==="
echo "Target: beat Codex 61.5% via benchmark maxxing (multi-variant strategy)"
echo ""

if [ ! -f "src/meta_autocode/maxxing.py" ]; then
    echo "FAIL: src/meta_autocode/maxxing.py not found"
    exit 1
fi

echo "Running pytest..."
python -m pytest tests/test_maxxing.py -v --tb=short
TEST_EXIT=$?

if [ $TEST_EXIT -eq 0 ]; then
    echo ""
    echo "PASS: BenchmarkMaxxer implemented. meta-autocode Phase 3 complete."
    echo "Next: TASK-004 (full integration — PIV + context + maxxing pipeline)."
else
    echo ""
    echo "FAIL: Tests failed (exit $TEST_EXIT)."
fi

exit $TEST_EXIT
