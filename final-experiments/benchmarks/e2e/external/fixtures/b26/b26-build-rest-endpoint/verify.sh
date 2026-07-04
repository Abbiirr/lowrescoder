#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: app.py exists
if [ ! -f "project/app.py" ]; then
    echo "FAIL: project/app.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/app.py exists"
fi

# Check 2: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_app.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
PASSED=$(echo "$TEST_OUTPUT" | grep -c "PASSED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All $PASSED tests pass"
fi
cd ..

# Check 3: POST endpoint returns 201
RESULT=$(cd project && python -c "
import json
from app import app
c = app.test_client()
r = c.post('/products', data=json.dumps({'name': 'X', 'price': 1.0}), content_type='application/json')
print('OK' if r.status_code == 201 else f'FAIL: {r.status_code}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: POST returns 201"
else
    echo "FAIL: POST status code wrong: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: GET non-existent returns 404
RESULT=$(cd project && python -c "
from app import app
c = app.test_client()
r = c.get('/products/nonexistent')
print('OK' if r.status_code == 404 else f'FAIL: {r.status_code}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: GET non-existent returns 404"
else
    echo "FAIL: GET non-existent status code wrong: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: POST missing required field returns 400
RESULT=$(cd project && python -c "
import json
from app import app
c = app.test_client()
r = c.post('/products', data=json.dumps({'price': 1.0}), content_type='application/json')
print('OK' if r.status_code == 400 else f'FAIL: {r.status_code}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: POST missing name returns 400"
else
    echo "FAIL: POST missing name status code wrong: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Full CRUD cycle works
RESULT=$(cd project && python -c "
import json
from app import app, store
store._products = {}
c = app.test_client()
# Create
r1 = c.post('/products', data=json.dumps({'name': 'W', 'price': 5.0}), content_type='application/json')
pid = json.loads(r1.data)['id']
# Read
r2 = c.get(f'/products/{pid}')
# Update
r3 = c.put(f'/products/{pid}', data=json.dumps({'name': 'W2'}), content_type='application/json')
# Delete
r4 = c.delete(f'/products/{pid}')
# Verify deleted
r5 = c.get(f'/products/{pid}')
if r1.status_code == 201 and r2.status_code == 200 and r3.status_code == 200 and r4.status_code == 200 and r5.status_code == 404:
    print('OK')
else:
    print(f'FAIL: {r1.status_code},{r2.status_code},{r3.status_code},{r4.status_code},{r5.status_code}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Full CRUD cycle works"
else
    echo "FAIL: CRUD cycle broken: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
