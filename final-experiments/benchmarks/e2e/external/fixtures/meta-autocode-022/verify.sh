#!/usr/bin/env bash
set -e
echo "=== TASK-022: Wiki Name Sanitizer Consecutive Space Fix ==="
echo "Pattern: go-gitea/gitea wiki filename sanitization"
echo ""
[ -f "src/wiki_name.py" ] || { echo "FAIL: wiki_name.py not found"; exit 1; }
python -m pytest tests/test_wiki_name.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: sanitize_wiki_name() collapses consecutive spaces." || echo "FAIL"
exit $TEST_EXIT
