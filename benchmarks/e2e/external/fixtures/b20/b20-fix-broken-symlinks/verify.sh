#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: No broken symlinks anywhere in project/
BROKEN=$(find project/ -type l ! -exec test -e {} \; -print 2>/dev/null)
if [ -n "$BROKEN" ]; then
    echo "FAIL: Broken symlinks found: $BROKEN"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No broken symlinks in project/"
fi

# Check 2: All config symlinks exist and are symlinks (not regular files)
for f in db.conf cache.conf auth.conf logging.conf routes.conf; do
    if [ ! -L "project/config/$f" ]; then
        echo "FAIL: project/config/$f is not a symbolic link"
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS: project/config/$f is a symbolic link"
    fi
done

# Check 3: bin/run exists and is a symlink
if [ ! -L "project/bin/run" ]; then
    echo "FAIL: project/bin/run is not a symbolic link"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/bin/run is a symbolic link"
fi

# Check 4: Config symlinks resolve and have correct content
if grep -q "pool_size = 20" project/config/db.conf 2>/dev/null; then
    echo "PASS: db.conf content is correct"
else
    echo "FAIL: db.conf content is wrong or unreadable"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "backend = redis" project/config/cache.conf 2>/dev/null; then
    echo "PASS: cache.conf content is correct"
else
    echo "FAIL: cache.conf content is wrong or unreadable"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "provider = oauth2" project/config/auth.conf 2>/dev/null; then
    echo "PASS: auth.conf content is correct"
else
    echo "FAIL: auth.conf content is wrong or unreadable"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "rotate = daily" project/config/logging.conf 2>/dev/null; then
    echo "PASS: logging.conf content is correct"
else
    echo "FAIL: logging.conf content is wrong or unreadable"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "api_prefix = /api/v2" project/config/routes.conf 2>/dev/null; then
    echo "PASS: routes.conf content is correct"
else
    echo "FAIL: routes.conf content is wrong or unreadable"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: bin/run symlink resolves and points to startup script
if grep -q "Starting application" project/bin/run 2>/dev/null; then
    echo "PASS: bin/run content is correct"
else
    echo "FAIL: bin/run content is wrong or unreadable"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Original files in vendor/lib/ are untouched
if [ "$(wc -l < project/vendor/lib/db.conf)" -eq 5 ]; then
    echo "PASS: vendor/lib/db.conf is intact"
else
    echo "FAIL: vendor/lib/db.conf has been modified"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
