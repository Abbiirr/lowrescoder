#!/usr/bin/env bash
set -euo pipefail
cd repo

ERRORS=0

# Check 1: No MERGE_HEAD (merge completed)
if [ -f .git/MERGE_HEAD ]; then
    echo "FAIL: Merge not completed (MERGE_HEAD still exists)"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: Merge completed"
fi

# Check 2: config.py has both DATABASE_URL and CACHE_TTL
if grep -q "DATABASE_URL" config.py && grep -q "CACHE_TTL" config.py; then
    echo "PASS: config.py has both DATABASE_URL and CACHE_TTL"
else
    echo "FAIL: config.py missing DATABASE_URL or CACHE_TTL"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: No conflict markers
if grep -qE '<<<<<<<|=======|>>>>>>>' config.py app.py 2>/dev/null; then
    echo "FAIL: Conflict markers still present"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No conflict markers"
fi

# Check 4: app.py imports both database and cache
if grep -q "database" app.py && grep -q "cache" app.py; then
    echo "PASS: app.py imports both database and cache"
else
    echo "FAIL: app.py missing database or cache import"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Clean working tree
DIRTY=$(git status --porcelain 2>/dev/null)
if [ -n "$DIRTY" ]; then
    echo "FAIL: Working tree is not clean"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: Working tree is clean"
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
