#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: package-lock.json exists
if [ -f "package-lock.json" ]; then
    echo "PASS: package-lock.json exists"
else
    echo "FAIL: package-lock.json not found"
    ERRORS=$((ERRORS + 1))
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

# Check 2: package-lock.json is valid JSON
if python -c "import json; json.load(open('package-lock.json'))" 2>/dev/null; then
    echo "PASS: package-lock.json is valid JSON"
else
    echo "FAIL: package-lock.json is not valid JSON"
    ERRORS=$((ERRORS + 1))
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

# Check 3: All package.json deps are in lock file
DEP_CHECK=$(python -c "
import json

pkg = json.load(open('package.json'))
lock = json.load(open('package-lock.json'))

# Collect all lock entries (look in packages or dependencies)
lock_text = json.dumps(lock)

required_deps = list(pkg.get('dependencies', {}).keys()) + list(pkg.get('devDependencies', {}).keys())
missing = []
for dep in required_deps:
    # Check in node_modules/ entries or top-level dependencies
    if f'\"node_modules/{dep}\"' not in lock_text and f'\"{dep}\"' not in lock_text:
        missing.append(dep)

if missing:
    print(f'MISSING:{\"|\".join(missing)}')
else:
    print('ok')
" 2>&1)

if [ "$DEP_CHECK" = "ok" ]; then
    echo "PASS: All package.json dependencies present in lock file"
else
    echo "FAIL: Dependencies missing from lock file: $DEP_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: No removed deps (moment) still in lock file
REMOVED_CHECK=$(python -c "
import json

pkg = json.load(open('package.json'))
lock = json.load(open('package-lock.json'))

all_pkg_deps = set(pkg.get('dependencies', {}).keys()) | set(pkg.get('devDependencies', {}).keys())
lock_text = json.dumps(lock)

# moment was removed from package.json — should not be in lock
extras = []
for removed in ['moment']:
    if removed not in all_pkg_deps and f'node_modules/{removed}' in lock_text:
        extras.append(removed)

if extras:
    print(f'EXTRA:{\"|\".join(extras)}')
else:
    print('ok')
" 2>&1)

if [ "$REMOVED_CHECK" = "ok" ]; then
    echo "PASS: No removed dependencies in lock file"
else
    echo "FAIL: Removed dependencies still in lock file: $REMOVED_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Lock file version matches package.json version
VERSION_CHECK=$(python -c "
import json
pkg = json.load(open('package.json'))
lock = json.load(open('package-lock.json'))
pkg_ver = pkg.get('version', '')
lock_ver = lock.get('version', '')
# Also check the root package entry
root = lock.get('packages', {}).get('', {})
root_ver = root.get('version', lock_ver)
if pkg_ver == lock_ver or pkg_ver == root_ver:
    print('ok')
else:
    print(f'MISMATCH:pkg={pkg_ver},lock={lock_ver},root={root_ver}')
" 2>&1)

if [ "$VERSION_CHECK" = "ok" ]; then
    echo "PASS: Version in lock file matches package.json"
else
    echo "FAIL: Version mismatch: $VERSION_CHECK"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
