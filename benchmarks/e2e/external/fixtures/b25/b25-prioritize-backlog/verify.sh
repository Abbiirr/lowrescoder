#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: Prioritized file exists
if [ ! -f "project/prioritized.md" ]; then
    echo "FAIL: project/prioritized.md not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/prioritized.md exists"
fi

# Check 2: Substantial content
if [ -f "project/prioritized.md" ]; then
    LINES=$(wc -l < project/prioritized.md)
    if [ "$LINES" -lt 15 ]; then
        echo "FAIL: prioritized.md too short ($LINES lines)"
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS: prioritized.md has substantive content ($LINES lines)"
    fi
fi

# Check 3: High-impact/small-effort items (T1, T3) are in top tier
if [ -f "project/prioritized.md" ]; then
    # T1 and T3 are high-impact, small-effort — they should appear early
    T1_LINE=$(grep -n "T1" project/prioritized.md | head -1 | cut -d: -f1 || echo 999)
    T3_LINE=$(grep -n "T3" project/prioritized.md | head -1 | cut -d: -f1 || echo 999)
    T5_LINE=$(grep -n "T5" project/prioritized.md | head -1 | cut -d: -f1 || echo 999)
    if [ "$T1_LINE" -lt "$T5_LINE" ] && [ "$T3_LINE" -lt "$T5_LINE" ]; then
        echo "PASS: High-impact items (T1, T3) ranked before low-impact (T5)"
    else
        echo "FAIL: High-impact items not prioritized above low-impact items"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 4: All 10 tasks accounted for
if [ -f "project/prioritized.md" ]; then
    TASK_COUNT=0
    for i in $(seq 1 10); do
        if grep -q "T${i}" project/prioritized.md 2>/dev/null; then
            TASK_COUNT=$((TASK_COUNT + 1))
        fi
    done
    if [ "$TASK_COUNT" -ge 9 ]; then
        echo "PASS: $TASK_COUNT of 10 tasks accounted for"
    else
        echo "FAIL: Only $TASK_COUNT of 10 tasks found in prioritized list"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 5: Multiple tiers/groups present
if [ -f "project/prioritized.md" ]; then
    TIERS=$(grep -cEi "(tier|first|next|later|drop|sprint|phase|priority|group)" project/prioritized.md || true)
    if [ "$TIERS" -ge 2 ]; then
        echo "PASS: Multiple priority tiers present"
    else
        echo "FAIL: Tasks not grouped into priority tiers"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 6: Methodology or rationale provided
if [ -f "project/prioritized.md" ]; then
    if grep -qEi "(methodolog|approach|rationale|impact.*effort|effort.*impact|matrix|framework|because|reason)" project/prioritized.md 2>/dev/null; then
        echo "PASS: Prioritization methodology/rationale provided"
    else
        echo "FAIL: No methodology or rationale for prioritization"
        ERRORS=$((ERRORS + 1))
    fi
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
