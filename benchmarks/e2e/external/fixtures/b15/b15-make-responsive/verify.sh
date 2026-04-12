#!/usr/bin/env bash
# Grading script for b15-make-responsive
set -euo pipefail

ERRORS=0

# Find the HTML file
HTML_FILE=""
for f in dashboard.html index.html; do
    if [ -f "$f" ]; then
        HTML_FILE="$f"
        break
    fi
done

if [ -z "$HTML_FILE" ]; then
    echo "FAIL: No HTML file found"
    exit 1
fi

# Find the CSS file(s)
CSS_FILE=""
for f in style.css styles.css dashboard.css; do
    if [ -f "$f" ]; then
        CSS_FILE="$f"
        break
    fi
done

# Check 1: Viewport meta tag exists
if grep -qiE 'viewport' "$HTML_FILE"; then
    echo "PASS: Viewport meta tag found"
else
    echo "FAIL: No viewport meta tag found in $HTML_FILE"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: CSS has media queries
MEDIA_FOUND=0
if [ -n "$CSS_FILE" ] && grep -qE '@media' "$CSS_FILE"; then
    MEDIA_FOUND=1
fi
# Also check inline styles
if grep -qE '@media' "$HTML_FILE"; then
    MEDIA_FOUND=1
fi

if [ "$MEDIA_FOUND" -eq 1 ]; then
    echo "PASS: Media queries found"
else
    echo "FAIL: No media queries found in CSS"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: No fixed pixel widths > 768px remain in CSS
FIXED_WIDTH_COUNT=0
if [ -n "$CSS_FILE" ]; then
    # Extract width values, excluding those inside media queries and max-width
    # Look for width: <number>px where number > 768
    FIXED_WIDTH_COUNT=$(python3 -c "
import re
with open('$CSS_FILE') as f:
    content = f.read()

# Remove media query blocks for this check — we only care about base styles
# that still have huge fixed widths. But actually, the key check is that
# the main layout containers no longer use fixed widths > 768px in the
# base (non-media-query) styles.
# Simple approach: count width declarations with values > 768px
pattern = r'(?<!max-)(?<!min-)width\s*:\s*(\d+)px'
matches = re.findall(pattern, content)
large = [int(m) for m in matches if int(m) > 768]
print(len(large))
" 2>/dev/null)
fi

if [ "$FIXED_WIDTH_COUNT" -eq 0 ] || [ -z "$FIXED_WIDTH_COUNT" ]; then
    echo "PASS: No fixed pixel widths > 768px found"
else
    echo "FAIL: Found $FIXED_WIDTH_COUNT fixed pixel width(s) > 768px still in CSS"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Dashboard structure is preserved (content still exists)
if grep -q 'Total Users' "$HTML_FILE" && grep -q 'Revenue' "$HTML_FILE"; then
    echo "PASS: Dashboard content preserved"
else
    echo "FAIL: Dashboard content appears to be missing"
    ERRORS=$((ERRORS + 1))
fi

# Result
if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0
