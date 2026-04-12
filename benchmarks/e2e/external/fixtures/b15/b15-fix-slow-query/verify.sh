#!/usr/bin/env bash
# Grading script for b15-fix-slow-query
set -euo pipefail

ERRORS=0

# Re-seed the database to ensure clean state
python db.py

# Check 1: The N+1 query pattern is gone (no per-user department query in loop)
# Look for JOIN or subquery pattern instead of loop-based queries
if grep -qE '(JOIN|join)\s+departments' app.py; then
    echo "PASS: Query uses JOIN to fetch departments"
elif grep -qE 'SELECT.*FROM.*users.*departments' app.py; then
    echo "PASS: Query combines users and departments"
elif python3 -c "
import ast, sys
with open('app.py') as f:
    source = f.read()

# Count the number of .execute() calls inside get_user_list
tree = ast.parse(source)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == 'get_user_list':
        execute_count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute) and child.func.attr == 'execute':
                    execute_count += 1
        if execute_count <= 2:
            print('optimized')
            sys.exit(0)
        else:
            sys.exit(1)
sys.exit(1)
" 2>/dev/null; then
    echo "PASS: Query appears optimized (reduced execute calls)"
else
    echo "FAIL: N+1 query pattern still present — expected JOIN or combined query"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: No per-row department lookup in a loop
if grep -qE 'for.*user.*in.*users' app.py && grep -qE 'execute.*SELECT.*FROM departments.*WHERE' app.py; then
    echo "FAIL: Still doing per-row department SELECT inside a loop"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No per-row department lookup in loop"
fi

# Check 3: Tests still pass
if python -m pytest test_app.py -v > test_output.log 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    tail -20 test_output.log
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Output data is still correct
python3 << 'PYCHECK'
import sys
sys.path.insert(0, ".")
from db import setup_database
from app import get_user_list

setup_database()
users = get_user_list()

errors = 0

if len(users) != 100:
    print(f"FAIL: Expected 100 users, got {len(users)}")
    errors += 1
else:
    print("PASS: User count is correct (100)")

required_keys = {"id", "name", "email", "department_name"}
if users:
    actual_keys = set(users[0].keys())
    if not required_keys.issubset(actual_keys):
        print(f"FAIL: Missing keys. Expected {required_keys}, got {actual_keys}")
        errors += 1
    else:
        print("PASS: Output format correct")

dept_names = {u["department_name"] for u in users}
expected_depts = {"Engineering", "Marketing", "Sales", "Support", "HR"}
if dept_names != expected_depts:
    print(f"FAIL: Department names wrong. Expected {expected_depts}, got {dept_names}")
    errors += 1
else:
    print("PASS: Department names correct")

sys.exit(errors)
PYCHECK

if [ $? -ne 0 ]; then
    ERRORS=$((ERRORS + 1))
fi

# Result
if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0
