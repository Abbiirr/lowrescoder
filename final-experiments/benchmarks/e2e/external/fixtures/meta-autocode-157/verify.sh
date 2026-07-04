#!/usr/bin/env bash
set -e
echo "=== TASK-157: Vowel Counter Off-by-One Fix ==="
[ -f "src/text_analyzer.py" ] || { echo "FAIL: text_analyzer.py not found"; exit 1; }
python -m pytest tests/test_text_analyzer.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: count_vowels() counts all vowels including first char." || echo "FAIL"
exit $TEST_EXIT
