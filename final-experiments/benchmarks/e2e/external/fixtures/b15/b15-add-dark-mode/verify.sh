#!/usr/bin/env bash
# Grading script for b15-add-dark-mode
set -euo pipefail

ERRORS=0

# Check 1: Dark mode setting exists in settings.py
if grep -qiE '(dark_mode|darkmode|dark_theme|theme.*dark)' settings.py; then
    echo "PASS: Dark mode setting found in settings.py"
else
    echo "FAIL: No dark mode setting found in settings.py"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: HTML has a toggle element for dark mode
TOGGLE_FOUND=0
for f in templates/settings.html templates/*.html settings.html; do
    if [ -f "$f" ]; then
        if grep -qiE '(dark.?mode|dark.?theme|theme.?toggle)' "$f" && \
           grep -qiE '(type="checkbox"|toggle|switch|<button)' "$f"; then
            TOGGLE_FOUND=1
            break
        fi
    fi
done

if [ "$TOGGLE_FOUND" -eq 1 ]; then
    echo "PASS: Dark mode toggle element found in HTML"
else
    echo "FAIL: No dark mode toggle element found in HTML"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: CSS has dark mode styles
DARK_CSS_FOUND=0
for f in static/style.css static/*.css style.css; do
    if [ -f "$f" ]; then
        if grep -qiE '(\.dark|dark-mode|dark-theme|prefers-color-scheme.*dark)' "$f"; then
            DARK_CSS_FOUND=1
            break
        fi
    fi
done

# Also check inline styles in HTML
if [ "$DARK_CSS_FOUND" -eq 0 ]; then
    for f in templates/settings.html templates/*.html settings.html; do
        if [ -f "$f" ]; then
            if grep -qiE '(\.dark|dark-mode|dark-theme|prefers-color-scheme.*dark)' "$f"; then
                DARK_CSS_FOUND=1
                break
            fi
        fi
    done
fi

if [ "$DARK_CSS_FOUND" -eq 1 ]; then
    echo "PASS: Dark mode CSS styles found"
else
    echo "FAIL: No dark mode CSS styles found"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Dark styles include dark background color
DARK_BG_FOUND=0
for f in static/style.css static/*.css style.css templates/settings.html templates/*.html settings.html; do
    if [ -f "$f" ]; then
        if grep -qiE 'background(-color)?:\s*#[0-3]' "$f" || \
           grep -qiE 'background(-color)?:\s*(black|#000|#111|#222|#333|rgb\([0-5][0-9]?)' "$f"; then
            DARK_BG_FOUND=1
            break
        fi
    fi
done

if [ "$DARK_BG_FOUND" -eq 1 ]; then
    echo "PASS: Dark background color found in styles"
else
    echo "FAIL: No dark background color found in styles"
    ERRORS=$((ERRORS + 1))
fi

# Result
if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0
