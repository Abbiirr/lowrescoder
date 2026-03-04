#!/usr/bin/env bash
# Setup for tb-003-fix-permissions
# Creates a webapp directory tree with deliberately broken permissions.
set -euo pipefail

# Create the webapp structure
mkdir -p webapp/public/css
mkdir -p webapp/public/js
mkdir -p webapp/public/images
mkdir -p webapp/config
mkdir -p webapp/logs
mkdir -p webapp/scripts

# Create files
echo "<html><body>Hello</body></html>" > webapp/public/index.html
echo "body { color: black; }" > webapp/public/css/style.css
echo "console.log('app');" > webapp/public/js/app.js
echo "placeholder" > webapp/public/images/logo.png
echo "DB_PASSWORD=secret123" > webapp/config/database.yml
echo "SECRET_KEY=abc123" > webapp/config/secrets.env
echo "log entry" > webapp/logs/app.log
echo "#!/bin/bash\necho deploy" > webapp/scripts/deploy.sh
echo "#!/bin/bash\necho backup" > webapp/scripts/backup.sh

# Now break the permissions:
# Config files should be 600 (owner-only) but are world-readable
chmod 777 webapp/config/database.yml
chmod 777 webapp/config/secrets.env

# Public directory should be 755 but is 000 (no access)
chmod 000 webapp/public

# Scripts should be 750 (owner+group exec) but have no execute bit
chmod 644 webapp/scripts/deploy.sh
chmod 644 webapp/scripts/backup.sh

# Logs dir should be 750 but is world-writable
chmod 777 webapp/logs
chmod 666 webapp/logs/app.log

# Config dir should be 750
chmod 777 webapp/config

echo "Setup complete. Webapp has broken permissions."
