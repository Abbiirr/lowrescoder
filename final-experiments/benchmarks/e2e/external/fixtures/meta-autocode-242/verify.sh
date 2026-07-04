#!/usr/bin/env bash
set -e
echo "=== TASK-242: summarize_memo Off-By-One Fix ==="
[ -f "src/memo_summarizer.py" ] || { echo "FAIL: memo_summarizer.py not found"; exit 1; }
python -m pytest tests/test_memo_summarizer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: summarize_memo() returns max_words words." || echo "FAIL"
exit $TEST_EXIT
