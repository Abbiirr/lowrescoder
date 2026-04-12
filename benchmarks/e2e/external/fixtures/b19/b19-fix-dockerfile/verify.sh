#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: Base image uses a valid tag (python:3.11-slim)
if grep -qE '^FROM python:3\.11-slim' Dockerfile; then
    echo "PASS: Base image uses python:3.11-slim"
else
    echo "FAIL: Base image is not python:3.11-slim"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: No reference to nonexistent 'ultraslim' tag
if grep -qi 'ultraslim' Dockerfile; then
    echo "FAIL: Dockerfile still references nonexistent 'ultraslim' tag"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No 'ultraslim' reference"
fi

# Check 3: WORKDIR is set
if grep -qE '^WORKDIR\s+' Dockerfile; then
    echo "PASS: WORKDIR is set"
else
    echo "FAIL: WORKDIR is not set"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: WORKDIR appears before COPY
WORKDIR_LINE=$(grep -n '^WORKDIR' Dockerfile | head -1 | cut -d: -f1)
COPY_LINE=$(grep -n '^COPY' Dockerfile | head -1 | cut -d: -f1)
if [ -n "$WORKDIR_LINE" ] && [ -n "$COPY_LINE" ]; then
    if [ "$WORKDIR_LINE" -lt "$COPY_LINE" ]; then
        echo "PASS: WORKDIR comes before COPY"
    else
        echo "FAIL: WORKDIR must come before COPY"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "FAIL: Could not find WORKDIR or COPY lines"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: apt-get runs before COPY of application files
APT_LINE=$(grep -n 'apt-get' Dockerfile | head -1 | cut -d: -f1)
if [ -n "$APT_LINE" ] && [ -n "$COPY_LINE" ]; then
    if [ "$APT_LINE" -lt "$COPY_LINE" ]; then
        echo "PASS: apt-get install runs before COPY"
    else
        echo "FAIL: apt-get install should run before COPY for layer caching"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "FAIL: Could not find apt-get or COPY lines"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Dockerfile has valid structure (FROM, WORKDIR, RUN apt, COPY, RUN pip, EXPOSE, CMD)
# Verify key instructions exist
for instr in FROM WORKDIR COPY RUN EXPOSE CMD; do
    if grep -q "^$instr" Dockerfile; then
        echo "PASS: Dockerfile contains $instr instruction"
    else
        echo "FAIL: Dockerfile missing $instr instruction"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check 7: CMD references the app correctly
if grep -q 'app:app' Dockerfile; then
    echo "PASS: CMD references app:app"
else
    echo "FAIL: CMD does not reference app:app"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
