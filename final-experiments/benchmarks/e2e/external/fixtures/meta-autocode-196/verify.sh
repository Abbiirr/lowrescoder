#!/usr/bin/env bash
set -e
echo "=== TASK-196: Syntax Highlighter Extension Fix ==="
[ -f "src/syntax_detector.py" ] || { echo "FAIL: syntax_detector.py not found"; exit 1; }
python -m pytest tests/test_syntax_detector.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: should_highlight() handles uppercase extensions." || echo "FAIL"
exit $TEST_EXIT
