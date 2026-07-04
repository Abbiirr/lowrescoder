#!/usr/bin/env bash
set -e
echo "=== TASK-032: Gitea Issue Label Deduplication Fix ==="
echo "Pattern: go-gitea/gitea issue label management"
echo ""
[ -f "src/label_manager.py" ] || { echo "FAIL: label_manager.py not found"; exit 1; }
python -m pytest tests/test_label_manager.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: add_labels_to_issue() deduplicates correctly." || echo "FAIL"
exit $TEST_EXIT
