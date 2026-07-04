#!/usr/bin/env bash
set -e

echo "=== meta-autocode TASK-002 Verification ==="
echo "Target: beat Codex 61.5% via progressive context loading"
echo ""

if [ ! -f "src/meta_autocode/__init__.py" ]; then
    echo "FAIL: src/meta_autocode/__init__.py not found"
    exit 1
fi

if [ ! -f "src/meta_autocode/context.py" ]; then
    echo "FAIL: src/meta_autocode/context.py not found"
    exit 1
fi

echo "Running pytest..."
python -m pytest tests/test_context.py -v --tb=short
TEST_EXIT=$?

if [ $TEST_EXIT -eq 0 ]; then
    echo ""
    echo "PASS: ProgressiveContextLoader implemented. meta-autocode Phase 2 complete."
    echo "Next: TASK-003 (benchmark maxxing — harness-bench integration)."
else
    echo ""
    echo "FAIL: Tests failed (exit $TEST_EXIT)."
fi

exit $TEST_EXIT
