#!/usr/bin/env bash
set -euo pipefail

ERRORS=0

# Check 1: config.yaml is valid YAML
if python3 -c "import yaml; yaml.safe_load(open('config.yaml'))" 2>/dev/null; then
    echo "PASS: config.yaml is valid YAML"
else
    echo "FAIL: config.yaml has YAML parse errors"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: All required keys are present
KEYS_CHECK=$(python3 -c "
import yaml
config = yaml.safe_load(open('config.yaml'))
required = {
    'server': ['host', 'port'],
    'database': ['host', 'port', 'name'],
    'logging': ['level', 'file'],
}
missing = []
for section, keys in required.items():
    if section not in config or not isinstance(config[section], dict):
        missing.append(section)
        continue
    for key in keys:
        if key not in config[section]:
            missing.append(f'{section}.{key}')
if missing:
    print('missing:' + ','.join(missing))
else:
    print('ok')
" 2>/dev/null || echo "error")
if [ "$KEYS_CHECK" = "ok" ]; then
    echo "PASS: All required keys present"
else
    echo "FAIL: $KEYS_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: server.port is an integer
PORT_TYPE=$(python3 -c "
import yaml
config = yaml.safe_load(open('config.yaml'))
print(type(config['server']['port']).__name__)
" 2>/dev/null || echo "error")
if [ "$PORT_TYPE" = "int" ]; then
    echo "PASS: server.port is an integer"
else
    echo "FAIL: server.port is '$PORT_TYPE', expected int"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: database.port is an integer
DB_PORT_TYPE=$(python3 -c "
import yaml
config = yaml.safe_load(open('config.yaml'))
print(type(config['database']['port']).__name__)
" 2>/dev/null || echo "error")
if [ "$DB_PORT_TYPE" = "int" ]; then
    echo "PASS: database.port is an integer"
else
    echo "FAIL: database.port is '$DB_PORT_TYPE', expected int"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: logging.level is valid
LEVEL_CHECK=$(python3 -c "
import yaml
config = yaml.safe_load(open('config.yaml'))
level = config['logging']['level']
valid = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
print('ok' if level in valid else f'bad:{level}')
" 2>/dev/null || echo "error")
if [ "$LEVEL_CHECK" = "ok" ]; then
    echo "PASS: logging.level is valid"
else
    echo "FAIL: logging.level is $LEVEL_CHECK"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: App loads config successfully
if python3 app.py > /dev/null 2>&1; then
    echo "PASS: app.py loads config successfully"
else
    echo "FAIL: app.py fails to load config"
    ERRORS=$((ERRORS + 1))
fi

if [ "$ERRORS" -gt 0 ]; then
    echo "RESULT: $ERRORS check(s) failed"
    exit 1
fi
echo "RESULT: All checks passed"
exit 0
