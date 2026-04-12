#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: Evaluation file exists
if [ ! -f "project/evaluation.md" ]; then
    echo "FAIL: project/evaluation.md not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/evaluation.md exists"
fi

# Check 2: Substantial content
if [ -f "project/evaluation.md" ]; then
    LINES=$(wc -l < project/evaluation.md)
    if [ "$LINES" -lt 20 ]; then
        echo "FAIL: evaluation.md too short ($LINES lines)"
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS: evaluation.md has substantive content ($LINES lines)"
    fi
fi

# Check 3: Scalability discussed
if [ -f "project/evaluation.md" ]; then
    if grep -qEi "(scalab|scale|500K|growth|horizon)" project/evaluation.md 2>/dev/null; then
        echo "PASS: Scalability evaluation present"
    else
        echo "FAIL: Scalability not discussed"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 4: Cost discussed
if [ -f "project/evaluation.md" ]; then
    if grep -qEi "(cost|\\\$|budget|expense|infra)" project/evaluation.md 2>/dev/null; then
        echo "PASS: Cost evaluation present"
    else
        echo "FAIL: Cost not discussed"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 5: Complexity discussed
if [ -f "project/evaluation.md" ]; then
    if grep -qEi "(complex|simpl|oper.*overhead|maintain|learn)" project/evaluation.md 2>/dev/null; then
        echo "PASS: Complexity evaluation present"
    else
        echo "FAIL: Complexity not discussed"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 6: Winner selected and justified
if [ -f "project/evaluation.md" ]; then
    if grep -qEi "(winner|selected|choose|chose|recommend|decision)" project/evaluation.md 2>/dev/null; then
        echo "PASS: Winner selected"
    else
        echo "FAIL: No winner selected"
        ERRORS=$((ERRORS + 1))
    fi
    if grep -qEi "(justif|because|reason|due to|since|rationale)" project/evaluation.md 2>/dev/null; then
        echo "PASS: Justification provided"
    else
        echo "FAIL: No justification for selection"
        ERRORS=$((ERRORS + 1))
    fi
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
