#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: /status endpoint exists and returns correct JSON
STATUS_RESP=$(python -c "
from app import app
client = app.test_client()
resp = client.get('/status')
import json
print(json.dumps({'code': resp.status_code, 'data': resp.get_json()}))
" 2>/dev/null)

STATUS_CODE=$(echo "$STATUS_RESP" | python -c "import sys,json; print(json.load(sys.stdin)['code'])")
HAS_STATUS=$(echo "$STATUS_RESP" | python -c "import sys,json; d=json.load(sys.stdin)['data']; print('yes' if d.get('status')=='healthy' else 'no')")
HAS_VERSION=$(echo "$STATUS_RESP" | python -c "import sys,json; d=json.load(sys.stdin)['data']; print('yes' if d.get('version')=='1.1.0' else 'no')")

if [ "$STATUS_CODE" = "200" ] && [ "$HAS_STATUS" = "yes" ] && [ "$HAS_VERSION" = "yes" ]; then
    echo "PASS: /status endpoint returns correct JSON"
else
    echo "FAIL: /status endpoint missing or returns wrong data (code=$STATUS_CODE, status=$HAS_STATUS, version=$HAS_VERSION)"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: All 3 original tests still pass
ORIG_RESULT=$(python -m pytest test_app.py::test_index test_app.py::test_get_users test_app.py::test_create_user -v 2>&1)
ORIG_PASSED=$(echo "$ORIG_RESULT" | grep -c " PASSED" || true)

if [ "$ORIG_PASSED" -ge 3 ]; then
    echo "PASS: All 3 original tests still pass"
else
    echo "FAIL: Original tests broken ($ORIG_PASSED/3 passed)"
    echo "$ORIG_RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: New test for /status endpoint exists
if grep -q "def test.*status" test_app.py; then
    echo "PASS: Test for /status endpoint exists"
else
    echo "FAIL: No test for /status endpoint found in test_app.py"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Full test suite passes (including new test)
FULL_RESULT=$(python -m pytest test_app.py -v 2>&1)
if echo "$FULL_RESULT" | grep -q "failed"; then
    echo "FAIL: Full test suite has failures"
    echo "$FULL_RESULT"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: Full test suite passes"
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
