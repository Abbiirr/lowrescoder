#!/usr/bin/env bash
set -e
echo "=== TASK-084: memos Tag Extractor Hyphen Support Fix ==="
[ -f "src/tag_extractor.py" ] || { echo "FAIL: tag_extractor.py not found"; exit 1; }
python -m pytest tests/test_tag_extractor.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: extract_tags() handles hyphenated tags." || echo "FAIL"
exit $TEST_EXIT
