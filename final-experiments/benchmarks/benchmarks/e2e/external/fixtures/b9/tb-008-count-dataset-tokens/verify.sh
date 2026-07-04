#!/usr/bin/env bash
# Grading script for tb-008-count-dataset-tokens
set -euo pipefail

ERRORS=0

# Run the solution
OUTPUT=$(python count_tokens.py 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "FAIL: count_tokens.py exited with non-zero status"
    exit 1
fi

# Read expected values
EXPECTED_TOTAL=$(grep "^total:" .expected_counts.txt | cut -d: -f2)
EXPECTED_UNIQUE=$(grep "^unique:" .expected_counts.txt | cut -d: -f2)

# Parse actual output
ACTUAL_TOTAL=$(echo "$OUTPUT" | grep -i "^total:" | sed 's/[^0-9]//g')
ACTUAL_UNIQUE=$(echo "$OUTPUT" | grep -i "^unique:" | sed 's/[^0-9]//g')

if [ -z "$ACTUAL_TOTAL" ]; then
    echo "FAIL: Could not parse 'total:' from output"
    echo "Output was: $OUTPUT"
    ERRORS=$((ERRORS + 1))
elif [ "$ACTUAL_TOTAL" = "$EXPECTED_TOTAL" ]; then
    echo "PASS: Total token count correct ($ACTUAL_TOTAL)"
else
    echo "FAIL: Total tokens — expected $EXPECTED_TOTAL, got $ACTUAL_TOTAL"
    ERRORS=$((ERRORS + 1))
fi

if [ -z "$ACTUAL_UNIQUE" ]; then
    echo "FAIL: Could not parse 'unique:' from output"
    echo "Output was: $OUTPUT"
    ERRORS=$((ERRORS + 1))
elif [ "$ACTUAL_UNIQUE" = "$EXPECTED_UNIQUE" ]; then
    echo "PASS: Unique token count correct ($ACTUAL_UNIQUE)"
else
    echo "FAIL: Unique tokens — expected $EXPECTED_UNIQUE, got $ACTUAL_UNIQUE"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0
