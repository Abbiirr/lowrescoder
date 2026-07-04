#!/usr/bin/env bash
# Grading script for tb-007-extract-safely
set -euo pipefail

ERRORS=0

# Run the extractor
if ! python extract.py 2>/dev/null; then
    echo "FAIL: extract.py exited with non-zero status"
    exit 1
fi

# Check 1: Safe files were extracted
for f in "output/docs/readme.txt" "output/docs/config.json" "output/data.txt"; do
    if [ -f "$f" ]; then
        echo "PASS: $f extracted"
    else
        echo "FAIL: $f was not extracted"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check 2: Verify content of extracted files
if [ -f "output/docs/readme.txt" ]; then
    CONTENT=$(cat "output/docs/readme.txt")
    if [ "$CONTENT" = "README content" ]; then
        echo "PASS: readme.txt has correct content"
    else
        echo "FAIL: readme.txt has wrong content"
        ERRORS=$((ERRORS + 1))
    fi
fi

# Check 3: Evil traversal file must NOT exist
if [ -f "/tmp/evil_traversal.txt" ]; then
    echo "FAIL: Path traversal attack succeeded — /tmp/evil_traversal.txt exists"
    ERRORS=$((ERRORS + 1))
    rm -f /tmp/evil_traversal.txt
else
    echo "PASS: Path traversal blocked"
fi

# Check 4: Absolute path file must NOT exist
if [ -f "/tmp/abs_evil.txt" ]; then
    echo "FAIL: Absolute path attack succeeded — /tmp/abs_evil.txt exists"
    ERRORS=$((ERRORS + 1))
    rm -f /tmp/abs_evil.txt
else
    echo "PASS: Absolute path blocked"
fi

# Check 5: Symlink must NOT exist in output
if [ -L "output/sneaky_link" ]; then
    echo "FAIL: Symlink was extracted"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: Symlink blocked"
fi

# Check 6: blocked.log must exist and contain blocked entries
if [ -f "blocked.log" ]; then
    BLOCKED_COUNT=$(wc -l < blocked.log)
    if [ "$BLOCKED_COUNT" -ge 2 ]; then
        echo "PASS: blocked.log has $BLOCKED_COUNT entries"
    else
        echo "FAIL: blocked.log should have at least 2 entries, has $BLOCKED_COUNT"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "FAIL: blocked.log was not created"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0
