#!/usr/bin/env bash
set -euo pipefail

WORK_DIR="$(pwd)"
ERRORS=0

# Extract non-comment, non-blank lines from crontab
ENTRIES=$(grep -v '^\s*#' crontab.txt | grep -v '^\s*$')

# Check 1: Exactly 5 entries
ENTRY_COUNT=$(echo "$ENTRIES" | wc -l)
if [ "$ENTRY_COUNT" -eq 5 ]; then
    echo "PASS: Exactly 5 cron entries found"
else
    echo "FAIL: Expected 5 entries, found $ENTRY_COUNT"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: All entries have valid cron time specs (5 fields) + a command
while IFS= read -r line; do
    # Extract the 5 time fields
    FIELD_COUNT=$(echo "$line" | awk '{print NF}')
    if [ "$FIELD_COUNT" -lt 6 ]; then
        echo "FAIL: Entry has fewer than 6 fields (5 time + command): $line"
        ERRORS=$((ERRORS + 1))
        continue
    fi

    # Validate minute field (0-59 or */N or *)
    MINUTE=$(echo "$line" | awk '{print $1}')
    if echo "$MINUTE" | grep -qE '^(\*|(\*/[0-9]+)|([0-5]?[0-9](,[0-5]?[0-9])*))$'; then
        true
    else
        echo "FAIL: Invalid minute field '$MINUTE' in: $line"
        ERRORS=$((ERRORS + 1))
    fi

    # Validate hour field (0-23 or */N or *)
    HOUR=$(echo "$line" | awk '{print $2}')
    if echo "$HOUR" | grep -qE '^(\*|(\*/[0-9]+)|([0-9]|1[0-9]|2[0-3])(,([0-9]|1[0-9]|2[0-3]))*)$'; then
        true
    else
        echo "FAIL: Invalid hour field '$HOUR' in: $line"
        ERRORS=$((ERRORS + 1))
    fi
done <<< "$ENTRIES"

# Check 3: All 5 scripts are referenced
for script in backup.sh cleanup.sh report.sh health_check.sh rotate_logs.sh; do
    if echo "$ENTRIES" | grep -q "$script"; then
        echo "PASS: $script is referenced in crontab"
    else
        echo "FAIL: $script is NOT referenced in crontab"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check 4: All referenced scripts exist
while IFS= read -r line; do
    # Extract the command part (fields 6+)
    CMD=$(echo "$line" | awk '{for(i=6;i<=NF;i++) printf "%s ", $i; print ""}' | xargs)
    # Extract script path (first token of command)
    SCRIPT_PATH=$(echo "$CMD" | awk '{print $1}')
    if [ -f "$SCRIPT_PATH" ]; then
        echo "PASS: Script exists: $SCRIPT_PATH"
    else
        echo "FAIL: Script not found: $SCRIPT_PATH"
        ERRORS=$((ERRORS + 1))
    fi
done <<< "$ENTRIES"

# Check 5: No entry has more than 5 time fields before the command
# (detect the 6-field time spec error)
while IFS= read -r line; do
    # A valid cron line: 5 time fields + command. If field 6 looks like a number
    # or time pattern (not a path/command), it's likely a malformed 6th time field.
    FIELD6=$(echo "$line" | awk '{print $6}')
    if echo "$FIELD6" | grep -qE '^[0-9]+$' && ! echo "$FIELD6" | grep -q '/'; then
        echo "FAIL: Possible 6th time field detected ('$FIELD6'): $line"
        ERRORS=$((ERRORS + 1))
    fi
done <<< "$ENTRIES"

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
