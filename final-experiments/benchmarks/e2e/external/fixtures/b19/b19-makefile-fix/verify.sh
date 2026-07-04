#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: .PHONY declares all targets
for target in build test clean lint; do
    if grep -q "\.PHONY:.*$target" Makefile; then
        echo "PASS: .PHONY includes $target"
    else
        echo "FAIL: .PHONY missing $target"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check 2: Uses tabs for indentation (not spaces)
# Lines starting with spaces after a target are bugs
if python3 -c "
with open('Makefile') as f:
    lines = f.readlines()
in_recipe = False
for line in lines:
    if line.strip() and not line.startswith(('\t', '#', '.', ' ')) and line.strip().endswith(':'):
        in_recipe = True
        continue
    if in_recipe and line.startswith('    '):
        exit(1)  # space-indented recipe line
    if line.strip() == '':
        in_recipe = False
"; then
    echo "PASS: Uses tabs for recipe indentation"
else
    echo "FAIL: Still uses spaces for recipe indentation"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: clean uses rm -rf
if grep -q 'rm -rf' Makefile; then
    echo "PASS: clean uses rm -rf"
else
    echo "FAIL: clean does not use rm -rf"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: make test works
if make test > /dev/null 2>&1; then
    echo "PASS: make test succeeds"
else
    echo "FAIL: make test fails"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: make clean works
mkdir -p dist build __pycache__
if make clean > /dev/null 2>&1; then
    if [ ! -d "dist" ] && [ ! -d "build" ]; then
        echo "PASS: make clean removes directories"
    else
        echo "FAIL: make clean did not remove directories"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "FAIL: make clean fails"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
