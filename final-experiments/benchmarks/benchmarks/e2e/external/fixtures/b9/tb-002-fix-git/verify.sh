#!/usr/bin/env bash
# Grading script for tb-002-fix-git
set -euo pipefail

cd repo

ERRORS=0

# Check 1: Must be on main branch
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "DETACHED")
if [ "$BRANCH" != "main" ]; then
    echo "FAIL: Expected branch 'main', got '$BRANCH'"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: On branch 'main'"
fi

# Check 2: newfile.txt must exist with correct content
if [ ! -f newfile.txt ]; then
    echo "FAIL: newfile.txt does not exist"
    ERRORS=$((ERRORS + 1))
elif [ "$(cat newfile.txt)" != "important new work" ]; then
    echo "FAIL: newfile.txt has wrong content"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: newfile.txt exists with correct content"
fi

# Check 3: Working tree must be clean (everything committed)
DIRTY=$(git status --porcelain 2>/dev/null)
if [ -n "$DIRTY" ]; then
    echo "FAIL: Working tree is not clean:"
    echo "$DIRTY"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: Working tree is clean"
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0
