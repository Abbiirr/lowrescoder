#!/usr/bin/env bash
set -e
echo "=== TASK-096: gitea Label Matcher Case-Insensitive Fix ==="
[ -f "src/label_matcher.py" ] || { echo "FAIL: label_matcher.py not found"; exit 1; }
python -m pytest tests/test_label_matcher.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: find_matching_labels() is case-insensitive." || echo "FAIL"
exit $TEST_EXIT
