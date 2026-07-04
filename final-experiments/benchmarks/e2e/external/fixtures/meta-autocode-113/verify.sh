#!/usr/bin/env bash
set -e
echo "=== TASK-113: memos Markdown Stripper Backtick Removal Fix ==="
[ -f "src/markdown_stripper.py" ] || { echo "FAIL: markdown_stripper.py not found"; exit 1; }
python -m pytest tests/test_markdown_stripper.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: strip_markdown() removes backtick code spans." || echo "FAIL"
exit $TEST_EXIT
