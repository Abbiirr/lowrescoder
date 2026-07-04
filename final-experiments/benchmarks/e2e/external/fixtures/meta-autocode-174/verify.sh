#!/usr/bin/env bash
set -e
echo "=== TASK-174: Word Count Split Fix ==="
[ -f "src/text_stats.py" ] || { echo "FAIL: text_stats.py not found"; exit 1; }
python -m pytest tests/test_text_stats.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: count_words() handles empty/multi-space/tab correctly." || echo "FAIL"
exit $TEST_EXIT
