#!/usr/bin/env bash
set -e
echo "=== TASK-153: Title Case Apostrophe Fix ==="
[ -f "src/text_formatter.py" ] || { echo "FAIL: text_formatter.py not found"; exit 1; }
python -m pytest tests/test_text_formatter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: to_title_case() handles apostrophes correctly." || echo "FAIL"
exit $TEST_EXIT
