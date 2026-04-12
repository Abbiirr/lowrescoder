#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: organizer.py exists
if [ ! -f "project/organizer.py" ]; then
    echo "FAIL: project/organizer.py not found"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: project/organizer.py exists"
fi

# Run the organizer
cd project
python organizer.py inbox/ 2>&1 || true
cd ..

# Check 2: No regular files remain directly in inbox/
REMAINING_FILES=$(find project/inbox/ -maxdepth 1 -type f | wc -l)
if [ "$REMAINING_FILES" -eq 0 ]; then
    echo "PASS: No files remain in inbox/ root"
else
    echo "FAIL: $REMAINING_FILES file(s) still in inbox/ root"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Extension subdirectories created
EXPECTED_DIRS="txt py html css json csv md png jpg pdf misc"
for dir in $EXPECTED_DIRS; do
    if [ -d "project/inbox/$dir" ]; then
        echo "PASS: inbox/$dir/ directory exists"
    else
        echo "FAIL: inbox/$dir/ directory missing"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check 4: Total file count is still 20 (no files lost)
TOTAL=$(find project/inbox/ -type f | wc -l)
if [ "$TOTAL" -eq 20 ]; then
    echo "PASS: All 20 files accounted for"
else
    echo "FAIL: Expected 20 files, found $TOTAL"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Specific files in correct directories
CHECKS_OK=0
CHECKS_FAIL=0
for check in "txt/report.txt" "py/hello.py" "html/index.html" "css/style.css" "json/config.json" "csv/users.csv" "md/readme.md" "png/logo.png" "pdf/document.pdf" "misc/LICENSE"; do
    if [ -f "project/inbox/$check" ]; then
        CHECKS_OK=$((CHECKS_OK + 1))
    else
        echo "FAIL: project/inbox/$check not found"
        CHECKS_FAIL=$((CHECKS_FAIL + 1))
    fi
done
if [ "$CHECKS_FAIL" -eq 0 ]; then
    echo "PASS: All $CHECKS_OK spot-checked files in correct directories"
else
    echo "FAIL: $CHECKS_FAIL spot-checked file(s) misplaced"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
