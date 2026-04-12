#!/usr/bin/env bash
set -euo pipefail

mkdir -p project/vendor/lib project/config project/bin

# Create library/config files in vendor/lib (the moved location)
cat > project/vendor/lib/db.conf << 'CONF'
[database]
host = localhost
port = 5432
name = production_db
pool_size = 20
CONF

cat > project/vendor/lib/cache.conf << 'CONF'
[cache]
backend = redis
host = 127.0.0.1
port = 6379
ttl = 3600
CONF

cat > project/vendor/lib/auth.conf << 'CONF'
[auth]
provider = oauth2
token_expiry = 900
refresh_enabled = true
max_sessions = 5
CONF

cat > project/vendor/lib/logging.conf << 'CONF'
[logging]
level = INFO
format = %(asctime)s %(levelname)s %(message)s
file = /var/log/app.log
rotate = daily
CONF

cat > project/vendor/lib/routes.conf << 'CONF'
[routes]
api_prefix = /api/v2
health_check = /health
docs = /docs
admin = /admin
CONF

cat > project/vendor/lib/startup.sh << 'SCRIPT'
#!/usr/bin/env bash
echo "Starting application..."
source /etc/app/env
exec python -m app.server
SCRIPT
chmod +x project/vendor/lib/startup.sh

# Create broken symlinks pointing to the OLD location (../lib/ which no longer exists)
# These are the symlinks the agent needs to fix
cd project/config
ln -s ../lib/db.conf db.conf
ln -s ../lib/cache.conf cache.conf
ln -s ../lib/auth.conf auth.conf
ln -s ../lib/logging.conf logging.conf
ln -s ../lib/routes.conf routes.conf
cd ../..

# Also a broken symlink in bin/
cd project/bin
ln -s ../lib/startup.sh run
cd ../..

echo "Setup complete. Project has 6 broken symlinks after lib/ was moved to vendor/lib/."
