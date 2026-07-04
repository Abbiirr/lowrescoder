#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: Script runs successfully
if bash build.sh > /dev/null 2>&1; then
    echo "PASS: build.sh exits 0"
else
    echo "FAIL: build.sh exits non-zero"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: dist/ directory created
if [ -d "dist" ]; then
    echo "PASS: dist/ directory exists"
else
    echo "FAIL: dist/ directory not created"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: No backticks in script
if grep -q '`' build.sh; then
    echo "FAIL: Script still uses backticks"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No backticks (uses \$() instead)"
fi

# Check 4: Variables are quoted
# Check that $SRC_DIR and $OUT_DIR usages are quoted
if grep -E '\$[A-Z_]+[^"]' build.sh | grep -vE '^\s*#|"\$|/\$|{\$' | grep -q '\$'; then
    echo "FAIL: Unquoted variable expansions found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: Variable expansions are quoted"
fi

# Check 5: Uses mkdir -p
if grep -q 'mkdir -p' build.sh; then
    echo "PASS: Uses mkdir -p"
else
    echo "FAIL: Does not use mkdir -p"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
