#!/usr/bin/env bash
set -euo pipefail
cd app

ERRORS=0

# Check 1: No MD5 used for password hashing
if grep -nE "hashlib\.md5" auth.py 2>/dev/null; then
    echo "FAIL: hashlib.md5 still used in auth.py"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No hashlib.md5 usage"
fi

# Check 2: No SHA1 used for password hashing
if grep -nE "hashlib\.sha1" auth.py 2>/dev/null; then
    echo "FAIL: hashlib.sha1 found in auth.py"
    ERRORS=$((ERRORS + 1))
else
    echo "PASS: No hashlib.sha1 usage"
fi

# Check 3: Secure hashing algorithm is used (bcrypt, argon2, or pbkdf2)
if grep -qE "(bcrypt|argon2|pbkdf2|pbkdf2_hmac|passlib)" auth.py 2>/dev/null; then
    echo "PASS: Secure password hashing algorithm detected"
else
    echo "FAIL: No secure hashing algorithm found (expected bcrypt, argon2, or pbkdf2)"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Password verification actually works end-to-end
python -c "
import sys
sys.path.insert(0, '.')
import auth, tempfile, os

with tempfile.TemporaryDirectory() as td:
    db = os.path.join(td, 'test.db')
    auth.init_db(db)
    auth.create_user('testuser', 'testpass123', db)
    user = auth.authenticate('testuser', 'testpass123', db)
    if user is None:
        print('FAIL: Password verification broken — valid credentials rejected')
        sys.exit(1)
    bad = auth.authenticate('testuser', 'wrongpass', db)
    if bad is not None:
        print('FAIL: Password verification broken — wrong password accepted')
        sys.exit(1)
    print('PASS: Password verification works correctly')
" 2>&1
if [ $? -ne 0 ]; then
    ERRORS=$((ERRORS + 1))
fi

# Check 5: All tests pass
if python -m pytest test_app.py -v 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests failed"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
