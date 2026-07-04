#!/usr/bin/env bash
set -e
echo "=== TASK-040: memos Word Count Whitespace Fix ==="
echo "Pattern: usememos/memos memo word count"
echo ""
[ -f "src/word_count.py" ] || { echo "FAIL: word_count.py not found"; exit 1; }
python -m pytest tests/test_word_count.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: count_words() handles all whitespace types." || echo "FAIL"
exit $TEST_EXIT
