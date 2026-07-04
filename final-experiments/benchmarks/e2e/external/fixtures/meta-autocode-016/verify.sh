#!/usr/bin/env bash
set -e
echo "=== TASK-016: Tag Parser Trailing Punctuation Fix ==="
echo "Pattern: usememos/memos hashtag extraction"
echo ""
[ -f "src/tag_parser.py" ] || { echo "FAIL: tag_parser.py not found"; exit 1; }
python -m pytest tests/test_tag_parser.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: extract_tags() strips trailing punctuation." || echo "FAIL"
exit $TEST_EXIT
