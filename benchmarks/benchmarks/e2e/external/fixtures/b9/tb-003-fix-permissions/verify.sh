#!/usr/bin/env bash
# Grading script for tb-003-fix-permissions
set -euo pipefail

ERRORS=0

check_perm() {
    local path="$1"
    local expected="$2"
    local actual
    actual=$(stat -c '%a' "$path" 2>/dev/null || echo "MISSING")
    if [ "$actual" != "$expected" ]; then
        echo "FAIL: $path — expected $expected, got $actual"
        ERRORS=$((ERRORS + 1))
    else
        echo "PASS: $path — $actual"
    fi
}

# Public directories: 755
check_perm "webapp/public" "755"
check_perm "webapp/public/css" "755"
check_perm "webapp/public/js" "755"
check_perm "webapp/public/images" "755"

# Public files: 644
check_perm "webapp/public/index.html" "644"
check_perm "webapp/public/css/style.css" "644"
check_perm "webapp/public/js/app.js" "644"
check_perm "webapp/public/images/logo.png" "644"

# Config directory: 750, files: 600
check_perm "webapp/config" "750"
check_perm "webapp/config/database.yml" "600"
check_perm "webapp/config/secrets.env" "600"

# Logs directory: 750, files: 640
check_perm "webapp/logs" "750"
check_perm "webapp/logs/app.log" "640"

# Scripts directory: 750, files: 750
check_perm "webapp/scripts" "750"
check_perm "webapp/scripts/deploy.sh" "750"
check_perm "webapp/scripts/backup.sh" "750"

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS permission check(s) failed"
    exit 1
fi

echo "RESULT: All permission checks passed"
exit 0
