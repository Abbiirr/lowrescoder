#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: config.json exists
if [ ! -f app/config.json ]; then
    echo "FAIL: app/config.json does not exist"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: app/config.json exists"
fi

# Check 2: config.json is valid JSON
if python3 -m json.tool app/config.json > /dev/null 2>&1; then
    echo "PASS: config.json is valid JSON"
else
    echo "FAIL: config.json is not valid JSON"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: config.json contains all required keys
for key in host port database debug; do
    if python3 -c "import json; c=json.load(open('app/config.json')); assert '$key' in c" 2>/dev/null; then
        echo "PASS: config.json contains key '$key'"
    else
        echo "FAIL: config.json missing required key '$key'"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check 4: Values match the backup
MATCH=$(python3 -c "
import json
with open('app/config.json') as f: curr = json.load(f)
with open('app/config.json.bak') as f: bak = json.load(f)
for key in ['host', 'port', 'database', 'debug']:
    if curr.get(key) != bak.get(key):
        print(f'MISMATCH: {key}')
        exit(1)
print('OK')
" 2>/dev/null || echo "ERROR")
if [ "$MATCH" = "OK" ]; then
    echo "PASS: Config values match backup"
else
    echo "FAIL: Config values do not match backup"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Application starts successfully
if python3 app/main.py > /dev/null 2>&1; then
    echo "PASS: Application starts successfully"
else
    echo "FAIL: Application failed to start"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
