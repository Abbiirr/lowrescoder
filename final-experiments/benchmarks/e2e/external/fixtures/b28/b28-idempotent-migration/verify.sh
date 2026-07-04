#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: migrate.py exists
if [ ! -f "project/migrate.py" ]; then
    echo "FAIL: project/migrate.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/migrate.py exists"
fi

# Check 2: Migration runs without error (second run)
RESULT=$(cd project && python -c "
from migrate import run_migration
try:
    run_migration()
    print('OK')
except Exception as e:
    print(f'FAIL: {e}')
" 2>&1 | tail -1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Migration runs without error (second run)"
else
    echo "FAIL: Migration crashed: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Third run also succeeds
RESULT=$(cd project && python -c "
from migrate import run_migration
try:
    run_migration()
    run_migration()
    print('OK')
except Exception as e:
    print(f'FAIL: {e}')
" 2>&1 | tail -1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: Third run also succeeds"
else
    echo "FAIL: Third run crashed: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: No duplicate data
RESULT=$(cd project && python -c "
import sqlite3
conn = sqlite3.connect('app.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM users WHERE username = \"admin\"')
users = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM settings')
settings = c.fetchone()[0]
conn.close()
if users == 1 and settings == 3:
    print('OK')
else:
    print(f'FAIL: admin={users}, settings={settings}')
" 2>&1)
if [ "$RESULT" = "OK" ]; then
    echo "PASS: No duplicate data"
else
    echo "FAIL: Duplicate data found: $RESULT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: All tests pass
cd project
TEST_OUTPUT=$(python -m pytest test_migrate.py -v 2>&1) || true
FAILED=$(echo "$TEST_OUTPUT" | grep -c "FAILED" || true)
if [ "$FAILED" -gt 0 ]; then
    echo "FAIL: $FAILED test(s) failed"
    echo "$TEST_OUTPUT" | grep "FAILED"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: All tests pass"
fi
cd ..

# Check 6: Uses IF NOT EXISTS or equivalent
if grep -qEi "(IF NOT EXISTS|CREATE.*OR|INSERT.*OR IGNORE|INSERT.*OR REPLACE|ON CONFLICT)" project/migrate.py 2>/dev/null; then
    echo "PASS: Uses idempotent SQL patterns"
else
    echo "FAIL: No idempotent SQL patterns detected"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
