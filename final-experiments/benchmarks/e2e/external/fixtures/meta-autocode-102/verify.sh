#!/usr/bin/env bash
set -e
echo "=== TASK-102: gitea Webhook Event Dispatch Logic Fix ==="
[ -f "src/webhook_dispatcher.py" ] || { echo "FAIL: webhook_dispatcher.py not found"; exit 1; }
python -m pytest tests/test_webhook_dispatcher.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: should_dispatch_event() only fires for subscribed events." || echo "FAIL"
exit $TEST_EXIT
