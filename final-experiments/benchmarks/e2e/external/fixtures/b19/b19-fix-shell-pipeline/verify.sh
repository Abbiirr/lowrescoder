#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: Script runs successfully
if bash pipeline.sh > /dev/null 2>&1; then
    echo "PASS: pipeline.sh exits 0"
else
    echo "FAIL: pipeline.sh exits non-zero"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: output.json exists
if [ -f "output.json" ]; then
    echo "PASS: output.json exists"
else
    echo "FAIL: output.json not created"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Output is valid JSON
if python3 -c "import json; json.load(open('output.json'))" 2>/dev/null; then
    echo "PASS: output.json is valid JSON"
else
    echo "FAIL: output.json is not valid JSON"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Output contains exactly 4 active records
RECORD_COUNT=$(python3 -c "
import json
data = json.load(open('output.json'))
print(len(data))
" 2>/dev/null || echo "0")
if [ "$RECORD_COUNT" = "4" ]; then
    echo "PASS: Output contains 4 active records"
else
    echo "FAIL: Expected 4 records, got $RECORD_COUNT"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Output is sorted by name alphabetically
SORTED_CHECK=$(python3 -c "
import json
data = json.load(open('output.json'))
names = [r['name'] for r in data]
print('sorted' if names == sorted(names) else 'unsorted')
" 2>/dev/null || echo "error")
if [ "$SORTED_CHECK" = "sorted" ]; then
    echo "PASS: Output is sorted by name"
else
    echo "FAIL: Output is not sorted by name"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: JSON fields are correct (name, email, status)
FIELDS_OK=$(python3 -c "
import json
data = json.load(open('output.json'))
for r in data:
    if set(r.keys()) != {'name', 'email', 'status'}:
        print('bad')
        exit()
    if r['status'] != 'active':
        print('bad')
        exit()
print('ok')
" 2>/dev/null || echo "bad")
if [ "$FIELDS_OK" = "ok" ]; then
    echo "PASS: All records have correct fields and active status"
else
    echo "FAIL: Records have wrong fields or non-active status"
    ERRORS=$((ERRORS + 1))
fi

# Check 7: No grep -P flag (non-portable)
if grep -q 'grep -P' pipeline.sh 2>/dev/null; then
    echo "FAIL: Script still uses non-portable grep -P flag"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No grep -P flag"
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
