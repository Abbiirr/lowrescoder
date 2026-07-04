#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: Review file exists
if [ ! -f "project/review.md" ]; then
    echo "FAIL: project/review.md not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/review.md exists"
fi

# Check 2: Review has substantial content
if [ -f "project/review.md" ]; then
    LINES=$(wc -l < project/review.md)
    if [ "$LINES" -lt 20 ]; then
        echo "FAIL: review.md too short ($LINES lines)"
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS: review.md has substantive content ($LINES lines)"
    fi
fi

# Check 3: SQL injection identified
if [ -f "project/review.md" ]; then
    if grep -qEi "(sql.?inject|f-string.*query|string.?format.*sql|unsanit|parameteriz)" project/review.md 2>/dev/null; then
        echo "PASS: SQL injection issue identified"
    else
        echo "FAIL: SQL injection issue not identified"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 4: Performance issue identified (no pagination or loading all)
if [ -f "project/review.md" ]; then
    if grep -qEi "(paginat|all.?users|fetchall|million|unbounded|load.?all|performance)" project/review.md 2>/dev/null; then
        echo "PASS: Performance issue identified"
    else
        echo "FAIL: Performance issue not identified"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 5: Password exposure or MD5 weakness identified
if [ -f "project/review.md" ]; then
    if grep -qEi "(password.*(expos|leak|field|return)|md5|weak.?hash|insecure.?token)" project/review.md 2>/dev/null; then
        echo "PASS: Security issue (password/MD5) identified"
    else
        echo "FAIL: Password exposure or MD5 weakness not identified"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 6: Approval/rejection stated
if [ -f "project/review.md" ]; then
    if grep -qEi "(approve|reject|request.?change|changes.?request)" project/review.md 2>/dev/null; then
        echo "PASS: Approval/rejection decision stated"
    else
        echo "FAIL: No approval/rejection decision stated"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 7: Suggestions provided (at least one fix suggestion)
if [ -f "project/review.md" ]; then
    if grep -qEi "(suggest|recommend|fix|should|instead|use.?parameteriz|prepared)" project/review.md 2>/dev/null; then
        echo "PASS: Suggestions/fixes provided"
    else
        echo "FAIL: No suggestions or fixes provided"
        ERRORS=$((ERRORS + 1))
    fi
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
