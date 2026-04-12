#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Use Python's sqlite3 module for all DB checks (more portable than sqlite3 CLI)
RESULT=$(python3 << 'PYVERIFY'
import sqlite3
import sys

errors = 0
conn = sqlite3.connect("app.db")
c = conn.cursor()

# Check 1: All 4 tables exist
for table in ["users", "posts", "comments", "tags"]:
    c.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", (table,))
    if c.fetchone()[0] == 1:
        print(f"PASS: Table '{table}' exists")
    else:
        print(f"FAIL: Table '{table}' does not exist")
        errors += 1

# Check 2: No duplicate tables
c.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name IN ('users','posts','comments','tags')")
total = c.fetchone()[0]
if total == 4:
    print("PASS: No duplicate tables (exactly 4 target tables)")
else:
    print(f"FAIL: Expected 4 target tables, found {total}")
    errors += 1

# Check 3: comments table has correct columns
c.execute("PRAGMA table_info(comments)")
cols = {row[1] for row in c.fetchall()}
if {"post_id", "author_id", "body"}.issubset(cols):
    print("PASS: comments table has correct columns")
else:
    print(f"FAIL: comments table has wrong columns: {cols}")
    errors += 1

# Check 4: tags table has correct columns
c.execute("PRAGMA table_info(tags)")
cols = {row[1] for row in c.fetchall()}
if {"name", "post_id"}.issubset(cols):
    print("PASS: tags table has correct columns")
else:
    print(f"FAIL: tags table has wrong columns: {cols}")
    errors += 1

# Check 5: Existing data preserved in users
c.execute("SELECT count(*) FROM users WHERE username='admin'")
if c.fetchone()[0] >= 1:
    print("PASS: Existing user data preserved")
else:
    print("FAIL: Existing user data lost")
    errors += 1

# Check 6: Existing data preserved in posts
c.execute("SELECT count(*) FROM posts WHERE title='First Post'")
if c.fetchone()[0] >= 1:
    print("PASS: Existing post data preserved")
else:
    print("FAIL: Existing post data lost")
    errors += 1

# Check 7: migration_log has completion entry
c.execute("SELECT count(*) FROM migration_log WHERE migration_name='001_initial_schema'")
if c.fetchone()[0] >= 1:
    print("PASS: migration_log has completion entry")
else:
    print("FAIL: migration_log missing completion entry")
    errors += 1

conn.close()
print(f"ERRORS:{errors}")
PYVERIFY
)

echo "$RESULT" | grep -v "^ERRORS:"

ERRORS=$(echo "$RESULT" | grep "^ERRORS:" | cut -d: -f2)

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
