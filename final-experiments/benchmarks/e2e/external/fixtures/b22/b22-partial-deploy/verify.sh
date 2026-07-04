#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: version.txt says 2.0
VERSION=$(cat webapp/version.txt 2>/dev/null | tr -d '[:space:]')
if [ "$VERSION" = "2.0" ]; then
    echo "PASS: version.txt is '2.0'"
else
    echo "FAIL: version.txt is '$VERSION', expected '2.0'"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: app.py has v2 health endpoint
if grep -q "/api/v2/health" webapp/app.py 2>/dev/null; then
    echo "PASS: app.py has /api/v2/health endpoint"
else
    echo "FAIL: app.py missing /api/v2/health endpoint"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: app.py has VERSION = "2.0"
if grep -q 'VERSION = "2.0"' webapp/app.py 2>/dev/null; then
    echo "PASS: app.py has VERSION = \"2.0\""
else
    echo "FAIL: app.py missing VERSION = \"2.0\""
    ERRORS=$((ERRORS + 1))
fi

# Check 4: index.html references v2.0
if grep -q "v2.0" webapp/templates/index.html 2>/dev/null; then
    echo "PASS: index.html references v2.0"
else
    echo "FAIL: index.html does not reference v2.0"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: index.html does NOT reference v1.0
if grep -q "v1.0" webapp/templates/index.html 2>/dev/null; then
    echo "FAIL: index.html still references v1.0"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: index.html has no v1.0 references"
fi

# Check 6: style.css has dark mode theme
if grep -q "dark" webapp/static/style.css 2>/dev/null; then
    echo "PASS: style.css has dark mode theme"
else
    echo "FAIL: style.css missing dark mode theme"
    ERRORS=$((ERRORS + 1))
fi

# Check 7: style.css does NOT have v1 light theme marker
if grep -q "v1.0" webapp/static/style.css 2>/dev/null; then
    echo "FAIL: style.css still has v1.0 reference"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: style.css has no v1.0 references"
fi

# Check 8: No v1.0 references in any deployed file (excluding bundle and manifest)
V1_REFS=$(grep -rl "v1\.0" webapp/version.txt webapp/app.py webapp/templates/index.html webapp/static/style.css 2>/dev/null || true)
if [ -z "$V1_REFS" ]; then
    echo "PASS: No v1.0 references in deployed files"
else
    echo "FAIL: v1.0 references found in: $V1_REFS"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
