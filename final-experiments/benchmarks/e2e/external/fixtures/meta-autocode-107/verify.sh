#!/usr/bin/env bash
set -e
echo "=== TASK-107: gitea Notification Filter Unread Logic Fix ==="
[ -f "src/notification_filter.py" ] || { echo "FAIL: notification_filter.py not found"; exit 1; }
python -m pytest tests/test_notification_filter.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: filter_notifications() returns unread when unread_only=True." || echo "FAIL"
exit $TEST_EXIT
