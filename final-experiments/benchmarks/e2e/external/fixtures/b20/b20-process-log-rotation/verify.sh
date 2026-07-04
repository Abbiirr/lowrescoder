#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# --- app.log checks ---

# Check 1: app.log exists and is truncated (< 100 lines)
if [ ! -f logs/app.log ]; then
    echo "FAIL: logs/app.log does not exist"
    ERRORS=$((ERRORS + 1))
else
    LINES=$(wc -l < logs/app.log)
    if [ "$LINES" -lt 100 ]; then
        echo "PASS: app.log is truncated ($LINES lines)"
    else
        echo "FAIL: app.log still has $LINES lines (expected < 100)"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 2: app.log.1.gz exists and is valid gzip
if [ ! -f logs/app.log.1.gz ]; then
    echo "FAIL: logs/app.log.1.gz does not exist"
    ERRORS=$((ERRORS + 1))
else
    if gzip -t logs/app.log.1.gz 2>/dev/null; then
        echo "PASS: app.log.1.gz is valid gzip"
    else
        echo "FAIL: app.log.1.gz is not valid gzip"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 3: app.log.1.gz contains the rotated data (should have 5000 lines from current app.log)
if [ -f logs/app.log.1.gz ]; then
    NEW_LINES=$(zcat logs/app.log.1.gz | wc -l)
    if [ "$NEW_LINES" -ge 4900 ]; then
        echo "PASS: app.log.1.gz has $NEW_LINES lines (from current log)"
    else
        echo "FAIL: app.log.1.gz has $NEW_LINES lines (expected ~5000 from rotated current log)"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 4: app.log.2.gz exists (shifted from old .1.gz) and is valid gzip
if [ ! -f logs/app.log.2.gz ]; then
    echo "FAIL: logs/app.log.2.gz does not exist (old .1.gz should be shifted here)"
    ERRORS=$((ERRORS + 1))
else
    if gzip -t logs/app.log.2.gz 2>/dev/null; then
        echo "PASS: app.log.2.gz is valid gzip"
    else
        echo "FAIL: app.log.2.gz is not valid gzip"
        ERRORS=$((ERRORS + 1))
    fi
    # Verify it contains the old rotation data
    OLD_LINES=$(zcat logs/app.log.2.gz | wc -l)
    if [ "$OLD_LINES" -ge 1900 ]; then
        echo "PASS: app.log.2.gz has $OLD_LINES lines (from old rotation)"
    else
        echo "FAIL: app.log.2.gz has $OLD_LINES lines (expected ~2000 from old .1.gz)"
        ERRORS=$((ERRORS + 1))
    fi
fi

# --- access.log checks ---

# Check 5: access.log exists and is truncated (< 100 lines)
if [ ! -f logs/access.log ]; then
    echo "FAIL: logs/access.log does not exist"
    ERRORS=$((ERRORS + 1))
else
    LINES=$(wc -l < logs/access.log)
    if [ "$LINES" -lt 100 ]; then
        echo "PASS: access.log is truncated ($LINES lines)"
    else
        echo "FAIL: access.log still has $LINES lines (expected < 100)"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 6: access.log.1.gz exists and is valid gzip
if [ ! -f logs/access.log.1.gz ]; then
    echo "FAIL: logs/access.log.1.gz does not exist"
    ERRORS=$((ERRORS + 1))
else
    if gzip -t logs/access.log.1.gz 2>/dev/null; then
        echo "PASS: access.log.1.gz is valid gzip"
    else
        echo "FAIL: access.log.1.gz is not valid gzip"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 7: access.log.1.gz contains rotated data (should have 3000 lines)
if [ -f logs/access.log.1.gz ]; then
    NEW_LINES=$(zcat logs/access.log.1.gz | wc -l)
    if [ "$NEW_LINES" -ge 2900 ]; then
        echo "PASS: access.log.1.gz has $NEW_LINES lines (from current log)"
    else
        echo "FAIL: access.log.1.gz has $NEW_LINES lines (expected ~3000 from rotated current log)"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 8: access.log.2.gz exists (shifted from old .1.gz) and is valid gzip
if [ ! -f logs/access.log.2.gz ]; then
    echo "FAIL: logs/access.log.2.gz does not exist (old .1.gz should be shifted here)"
    ERRORS=$((ERRORS + 1))
else
    if gzip -t logs/access.log.2.gz 2>/dev/null; then
        echo "PASS: access.log.2.gz is valid gzip"
    else
        echo "FAIL: access.log.2.gz is not valid gzip"
        ERRORS=$((ERRORS + 1))
    fi
    OLD_LINES=$(zcat logs/access.log.2.gz | wc -l)
    if [ "$OLD_LINES" -ge 1400 ]; then
        echo "PASS: access.log.2.gz has $OLD_LINES lines (from old rotation)"
    else
        echo "FAIL: access.log.2.gz has $OLD_LINES lines (expected ~1500 from old .1.gz)"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 9: No rotation beyond .3.gz
for f in logs/app.log.4.gz logs/access.log.4.gz; do
    if [ -f "$f" ]; then
        echo "FAIL: $f exists (should keep at most 3 rotations)"
        ERRORS=$((ERRORS + 1))
    fi
done
echo "PASS: No excess rotation files"

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
