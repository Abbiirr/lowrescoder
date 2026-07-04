#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: Answer file exists
if [ ! -f "project/answer.md" ]; then
    echo "FAIL: project/answer.md not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/answer.md exists"
fi

# Check 2: Answer file is not empty and has substantial content
if [ -f "project/answer.md" ]; then
    LINES=$(wc -l < project/answer.md)
    if [ "$LINES" -lt 15 ]; then
        echo "FAIL: answer.md too short ($LINES lines) — needs substantive content"
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS: answer.md has substantive content ($LINES lines)"
    fi
fi

# Check 3: Answer references at least one specific requirement
if [ -f "project/answer.md" ]; then
    if grep -qEi "(FR[0-9]|NFR[0-9]|concurrent|ACID|transaction|multi-user|full-text|access control)" project/answer.md 2>/dev/null; then
        echo "PASS: Answer references specific requirements"
    else
        echo "FAIL: Answer does not reference any specific requirements"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 4: A decision is stated
if [ -f "project/answer.md" ]; then
    if grep -qEi "(selected|choose|chose|decision|recommend|winner)" project/answer.md 2>/dev/null; then
        echo "PASS: A decision is clearly stated"
    else
        echo "FAIL: No clear decision stated"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 5: Trade-offs are discussed (mentions at least 2 options)
if [ -f "project/answer.md" ]; then
    MENTIONS=0
    grep -qEi "(sqlite|lite)" project/answer.md 2>/dev/null && MENTIONS=$((MENTIONS + 1))
    grep -qEi "(postgres|postgresql)" project/answer.md 2>/dev/null && MENTIONS=$((MENTIONS + 1))
    grep -qEi "(mongo|mongodb)" project/answer.md 2>/dev/null && MENTIONS=$((MENTIONS + 1))
    if [ "$MENTIONS" -ge 2 ]; then
        echo "PASS: Trade-offs discussed ($MENTIONS options mentioned)"
    else
        echo "FAIL: Only $MENTIONS option(s) mentioned — need trade-off discussion"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 6: Justification section has content
if [ -f "project/answer.md" ]; then
    if grep -qEi "(justif|because|reason|rationale|due to|since)" project/answer.md 2>/dev/null; then
        echo "PASS: Justification provided"
    else
        echo "FAIL: No justification provided for the decision"
        ERRORS=$((ERRORS + 1))
    fi
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
