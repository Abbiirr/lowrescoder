#!/usr/bin/env bash
set -e
echo "=== TASK-059: Gitea Webhook HMAC-SHA256 Fix ==="
[ -f "src/webhook_verifier.py" ] || { echo "FAIL: webhook_verifier.py not found"; exit 1; }
python -m pytest tests/test_webhook_verifier.py -v --tb=short
TEST_EXIT=$?
[ $TEST_EXIT -eq 0 ] && echo "PASS: verify_webhook_signature() uses SHA256." || echo "FAIL"
exit $TEST_EXIT
