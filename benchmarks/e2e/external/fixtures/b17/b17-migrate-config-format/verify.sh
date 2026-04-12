#!/usr/bin/env bash
# Grading script for b17-migrate-config-format
set -euo pipefail

ERRORS=0

# Check 1: config.yaml exists
if [ -f config.yaml ] || [ -f config.yml ]; then
    echo "PASS: YAML config file exists"
    YAML_FILE=$([ -f config.yaml ] && echo "config.yaml" || echo "config.yml")
else
    echo "FAIL: No config.yaml or config.yml found"
    ERRORS=$((ERRORS + 1))
    YAML_FILE=""
fi

# Check 2: config.ini is no longer referenced in Python files
INI_REFS=0
for f in app.py database.py logging_config.py server.py; do
    if [ -f "$f" ] && grep -qE 'config\.ini|configparser|ConfigParser' "$f"; then
        echo "FAIL: $f still references config.ini or configparser"
        INI_REFS=$((INI_REFS + 1))
    fi
done

if [ "$INI_REFS" -eq 0 ]; then
    echo "PASS: No Python files reference config.ini or configparser"
else
    ERRORS=$((ERRORS + 1))
fi

# Check 3: YAML file has the right data
if [ -n "$YAML_FILE" ]; then
    python3 << PYCHECK
import sys
import yaml

with open("$YAML_FILE") as f:
    cfg = yaml.safe_load(f)

errors = 0

# Check database section
if "database" not in cfg:
    print("FAIL: Missing database section in YAML")
    errors += 1
else:
    db = cfg["database"]
    if db.get("host") != "localhost" or db.get("port") != 5432:
        print("FAIL: Database config values incorrect")
        errors += 1
    else:
        print("PASS: Database config correct in YAML")

# Check server section
if "server" not in cfg:
    print("FAIL: Missing server section in YAML")
    errors += 1
else:
    srv = cfg["server"]
    if srv.get("port") != 8080:
        print("FAIL: Server port incorrect")
        errors += 1
    else:
        print("PASS: Server config correct in YAML")

# Check app section
if "app" not in cfg:
    print("FAIL: Missing app section in YAML")
    errors += 1
else:
    app = cfg["app"]
    if app.get("name") != "MyApplication":
        print("FAIL: App name incorrect")
        errors += 1
    else:
        print("PASS: App config correct in YAML")

sys.exit(errors)
PYCHECK

    PYCHECK_EXIT=$?
    if [ "$PYCHECK_EXIT" -ne 0 ]; then
        ERRORS=$((ERRORS + PYCHECK_EXIT))
    fi
fi

# Check 4: Python files use yaml module
YAML_IMPORTS=0
for f in app.py database.py logging_config.py server.py; do
    if [ -f "$f" ] && grep -qE 'import yaml|from yaml' "$f"; then
        YAML_IMPORTS=$((YAML_IMPORTS + 1))
    fi
done

if [ "$YAML_IMPORTS" -ge 4 ]; then
    echo "PASS: All 4 Python files import yaml"
else
    echo "FAIL: Expected 4 files to import yaml, found $YAML_IMPORTS"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: All tests pass
if python -m pytest test_config.py -v > test_output.log 2>&1; then
    echo "PASS: All tests pass"
else
    echo "FAIL: Tests do not pass"
    tail -20 test_output.log
    ERRORS=$((ERRORS + 1))
fi

# Result
if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi

echo "RESULT: All checks passed"
exit 0
