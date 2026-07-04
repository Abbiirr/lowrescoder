#!/usr/bin/env bash
set -e

# Verify meta-autocode Phase 1: PIV strategy implementation
# All 8 tests must pass.

echo "=== meta-autocode TASK-001 Verification ==="
echo "Target: beat Codex 61.5% baseline via PIV strategy"
echo ""

# Check src exists
if [ ! -f "src/meta_autocode/__init__.py" ]; then
    echo "FAIL: src/meta_autocode/__init__.py not found"
    exit 1
fi

if [ ! -f "src/meta_autocode/piv.py" ]; then
    echo "FAIL: src/meta_autocode/piv.py not found"
    exit 1
fi

if [ ! -f "src/meta_autocode/scorer.py" ]; then
    echo "FAIL: src/meta_autocode/scorer.py not found"
    exit 1
fi

# Run tests
echo "Running pytest..."
python -m pytest tests/test_piv.py -v --tb=short
TEST_EXIT=$?

if [ $TEST_EXIT -eq 0 ]; then
    echo ""
    echo "PASS: All tests passed. meta-autocode PIV phase complete."
    echo "Next: TASK-002 (ProgressiveContextLoader) to further widen the gap over Codex."
else
    echo ""
    echo "FAIL: Tests failed (exit $TEST_EXIT). Keep iterating."
fi

exit $TEST_EXIT
