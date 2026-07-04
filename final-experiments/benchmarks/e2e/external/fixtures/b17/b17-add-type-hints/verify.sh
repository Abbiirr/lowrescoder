#!/usr/bin/env bash
# Grading script for b17-add-type-hints
set -euo pipefail

ERRORS=0

# Check 1: All existing tests still pass
if python -m pytest test_all.py -v > test_output.log 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    tail -20 test_output.log
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Public functions have type hints (return type annotations)
python3 << 'PYCHECK'
import ast
import sys

errors = 0

files = ["data_processor.py", "text_utils.py", "math_helpers.py"]

for filepath in files:
    with open(filepath) as f:
        tree = ast.parse(f.read())

    untyped = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            # Check return annotation
            if node.returns is None:
                untyped.append(node.name)
            # Check parameter annotations (skip 'self')
            for arg in node.args.args:
                if arg.arg != "self" and arg.annotation is None:
                    if node.name not in untyped:
                        untyped.append(node.name)

    if untyped:
        print(f"FAIL: {filepath} has untyped public functions: {untyped}")
        errors += 1
    else:
        print(f"PASS: {filepath} all public functions have type hints")

sys.exit(errors)
PYCHECK

PYCHECK_EXIT=$?
if [ "$PYCHECK_EXIT" -ne 0 ]; then
    ERRORS=$((ERRORS + PYCHECK_EXIT))
fi

# Check 3: mypy passes
if python -m mypy data_processor.py text_utils.py math_helpers.py --config-file mypy.ini > mypy_output.log 2>&1; then
    echo "PASS: mypy type checking passes"
else
    echo "FAIL: mypy type checking fails"
    tail -20 mypy_output.log
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Functions still work correctly (behavior unchanged)
python3 << 'PYCHECK2'
import sys
from data_processor import filter_by_threshold, compute_stats
from text_utils import word_count, is_palindrome
from math_helpers import factorial, fibonacci

errors = 0

if filter_by_threshold([1, 5, 3], 3) != [5]:
    print("FAIL: filter_by_threshold behavior changed")
    errors += 1

if compute_stats([2, 4])["mean"] != 3.0:
    print("FAIL: compute_stats behavior changed")
    errors += 1

if word_count("a b c") != 3:
    print("FAIL: word_count behavior changed")
    errors += 1

if factorial(5) != 120:
    print("FAIL: factorial behavior changed")
    errors += 1

if fibonacci(5) != [0, 1, 1, 2, 3]:
    print("FAIL: fibonacci behavior changed")
    errors += 1

if errors == 0:
    print("PASS: All functions behave correctly")

sys.exit(errors)
PYCHECK2

PYCHECK2_EXIT=$?
if [ "$PYCHECK2_EXIT" -ne 0 ]; then
    ERRORS=$((ERRORS + PYCHECK2_EXIT))
fi

# Result
if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0
