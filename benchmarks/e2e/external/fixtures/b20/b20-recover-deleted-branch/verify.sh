#!/usr/bin/env bash
set -euo pipefail
cd repo

ERRORS=0

# Check 1: Branch exists
if git rev-parse --verify feature/important-work >/dev/null 2>&1; then
    echo "PASS: Branch feature/important-work exists"
else
    echo "FAIL: Branch feature/important-work does not exist"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: feature.py has do_important_work function
if git show feature/important-work:feature.py 2>/dev/null | grep -q "def do_important_work"; then
    echo "PASS: feature.py contains do_important_work()"
else
    echo "FAIL: feature.py missing do_important_work()"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Branch has at least 2 commits beyond main
BRANCH_COMMITS=$(git rev-list main..feature/important-work 2>/dev/null | wc -l)
if [ "$BRANCH_COMMITS" -ge 2 ]; then
    echo "PASS: Branch has $BRANCH_COMMITS commits"
else
    echo "FAIL: Branch has only $BRANCH_COMMITS commits (need >= 2)"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: main unchanged
MAIN_HEAD=$(git rev-parse main)
MAIN_FILES=$(git ls-tree --name-only main | sort)
if echo "$MAIN_FILES" | grep -q "README.md" && echo "$MAIN_FILES" | grep -q "version.py"; then
    echo "PASS: main branch unchanged"
else
    echo "FAIL: main branch was modified"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
