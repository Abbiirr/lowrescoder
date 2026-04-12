#!/usr/bin/env bash
set -euo pipefail
cd app

ERRORS=0

# Check 1: File type validation exists — code checks extension or mimetype
if grep -qE "(allowed_extensions|ALLOWED_EXTENSIONS|allowed_types|ALLOWED_TYPES|\.rsplit|splitext.*\.\w|mimetype|content_type)" app.py 2>/dev/null; then
    echo "PASS: File type validation detected in app.py"
else
    echo "FAIL: No file type validation found in app.py"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Dangerous file types are rejected (upload a .py file should fail)
python -c "
import sys, io
sys.path.insert(0, '.')
from app import app
app.config['TESTING'] = True
with app.test_client() as c:
    data = {'file': (io.BytesIO(b'import os; os.system(\"rm -rf /\")'), 'evil.py')}
    resp = c.post('/upload', data=data, content_type='multipart/form-data')
    if resp.status_code in (400, 403, 415, 422):
        print('PASS: Dangerous .py file rejected (HTTP {})'.format(resp.status_code))
    else:
        print('FAIL: Dangerous .py file was accepted (HTTP {})'.format(resp.status_code))
        sys.exit(1)
" 2>&1
if [ $? -ne 0 ]; then
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Files not stored in static/ directory
if grep -qE "static.*upload" app.py 2>/dev/null | head -1; then
    # Check if it's the actual UPLOAD_DIR assignment, not a comment
    if grep -E "UPLOAD_DIR.*=.*static" app.py 2>/dev/null | grep -vE "^\s*#"; then
        echo "FAIL: Files still stored in static/ directory"
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS: Upload directory moved out of static/"
    fi
else
    echo "PASS: Upload directory not in static/"
fi

# Check 4: Filename sanitization (secure_filename or equivalent)
if grep -qE "(secure_filename|werkzeug|sanitize|uuid|hashlib)" app.py 2>/dev/null; then
    echo "PASS: Filename sanitization detected"
else
    echo "FAIL: No filename sanitization found (expected secure_filename, uuid, or similar)"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: Path traversal attack blocked
python -c "
import sys, io
sys.path.insert(0, '.')
from app import app
app.config['TESTING'] = True
with app.test_client() as c:
    data = {'file': (io.BytesIO(b'traversal test'), '../../../etc/passwd')}
    resp = c.post('/upload', data=data, content_type='multipart/form-data')
    # Either rejected or filename sanitized (no ../ in stored path)
    if resp.status_code in (400, 403, 415, 422):
        print('PASS: Path traversal filename rejected')
    elif resp.status_code == 200:
        result = resp.get_json()
        stored = result.get('filename', '') + result.get('path', '')
        if '../' not in stored:
            print('PASS: Path traversal neutralized in stored filename')
        else:
            print('FAIL: Path traversal not blocked')
            sys.exit(1)
    else:
        print('FAIL: Unexpected response to path traversal: HTTP {}'.format(resp.status_code))
        sys.exit(1)
" 2>&1
if [ $? -ne 0 ]; then
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Existing tests still pass
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
