#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: ADR file exists
if [ ! -f "project/adr.md" ]; then
    echo "FAIL: project/adr.md not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/adr.md exists"
fi

# Check 2: Substantial content
if [ -f "project/adr.md" ]; then
    LINES=$(wc -l < project/adr.md)
    if [ "$LINES" -lt 20 ]; then
        echo "FAIL: adr.md too short ($LINES lines)"
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS: adr.md has substantive content ($LINES lines)"
    fi
fi

# Check 3: ADR has Status section
if [ -f "project/adr.md" ]; then
    if grep -qEi "^##.*status" project/adr.md 2>/dev/null; then
        echo "PASS: Status section present"
    else
        echo "FAIL: Status section missing"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 4: ADR has Context section
if [ -f "project/adr.md" ]; then
    if grep -qEi "^##.*context" project/adr.md 2>/dev/null; then
        echo "PASS: Context section present"
    else
        echo "FAIL: Context section missing"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 5: ADR has Decision section with a clear choice
if [ -f "project/adr.md" ]; then
    if grep -qEi "^##.*decision" project/adr.md 2>/dev/null; then
        echo "PASS: Decision section present"
    else
        echo "FAIL: Decision section missing"
        ERRORS=$((ERRORS + 1))
    fi
    if grep -qEi "(JWT|session|OAuth|Auth0|token)" project/adr.md 2>/dev/null; then
        echo "PASS: A specific option is referenced in the decision"
    else
        echo "FAIL: No specific option referenced in decision"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 6: ADR has Consequences section
if [ -f "project/adr.md" ]; then
    if grep -qEi "^##.*consequence" project/adr.md 2>/dev/null; then
        echo "PASS: Consequences section present"
    else
        echo "FAIL: Consequences section missing"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 7: Both positive and negative consequences listed
if [ -f "project/adr.md" ]; then
    HAS_POS=$(grep -cEi "(positive|pro|benefit|advantage|good)" project/adr.md || true)
    HAS_NEG=$(grep -cEi "(negative|con|downside|risk|trade-off|drawback)" project/adr.md || true)
    if [ "$HAS_POS" -gt 0 ] && [ "$HAS_NEG" -gt 0 ]; then
        echo "PASS: Both positive and negative consequences discussed"
    else
        echo "FAIL: Missing positive or negative consequences"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 8: All 3 options mentioned
if [ -f "project/adr.md" ]; then
    OPTS=0
    grep -qEi "JWT" project/adr.md 2>/dev/null && OPTS=$((OPTS + 1))
    grep -qEi "session" project/adr.md 2>/dev/null && OPTS=$((OPTS + 1))
    grep -qEi "(OAuth|Auth0|Okta)" project/adr.md 2>/dev/null && OPTS=$((OPTS + 1))
    if [ "$OPTS" -ge 3 ]; then
        echo "PASS: All 3 options considered"
    else
        echo "FAIL: Only $OPTS of 3 options mentioned"
        ERRORS=$((ERRORS + 1))
    fi
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
