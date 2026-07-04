#!/usr/bin/env bash
set -euo pipefail
cd app

ERRORS=0

# Check 1: URL validation exists in the code
if grep -qE "(urlparse|url_parse|is_safe_url|is_valid_redirect|ALLOWED_HOSTS|whitelist|validate.*url|safe.*redirect)" app.py 2>/dev/null; then
    echo "PASS: URL validation logic detected"
else
    echo "FAIL: No URL validation logic found in app.py"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: External URLs are rejected (should redirect to safe default)
python -c "
import sys
sys.path.insert(0, '.')
from app import app
app.config['TESTING'] = True
with app.test_client() as c:
    # Test various external/malicious URLs
    attacks = [
        'https://evil.com/steal-creds',
        'http://attacker.org/phish',
        '//evil.com/path',
        'https://evil.com@myapp.example.com',
    ]
    for url in attacks:
        resp = c.get(f'/callback?code=abc&redirect_url={url}')
        location = resp.headers.get('Location', '')
        if 'evil.com' in location or 'attacker.org' in location:
            print(f'FAIL: External redirect allowed to {url} -> {location}')
            sys.exit(1)
    print('PASS: All external redirect attempts blocked')
" 2>&1
if [ $? -ne 0 ]; then
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Internal redirects still work
python -c "
import sys
sys.path.insert(0, '.')
from app import app
app.config['TESTING'] = True
with app.test_client() as c:
    for path in ['/profile', '/settings', '/dashboard']:
        resp = c.get(f'/callback?code=abc&redirect_url={path}')
        location = resp.headers.get('Location', '')
        if path not in location:
            print(f'FAIL: Internal redirect to {path} broken — got {location}')
            sys.exit(1)
    print('PASS: Internal redirects work correctly')
" 2>&1
if [ $? -ne 0 ]; then
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Default redirect (no redirect_url) goes to /dashboard
python -c "
import sys
sys.path.insert(0, '.')
from app import app
app.config['TESTING'] = True
with app.test_client() as c:
    resp = c.get('/callback?code=abc')
    location = resp.headers.get('Location', '')
    if '/dashboard' in location:
        print('PASS: Default redirect goes to /dashboard')
    else:
        print(f'FAIL: Default redirect went to {location} instead of /dashboard')
        sys.exit(1)
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
