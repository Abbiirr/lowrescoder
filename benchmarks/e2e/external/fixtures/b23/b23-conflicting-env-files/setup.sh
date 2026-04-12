#!/usr/bin/env bash
set -euo pipefail

cat > .env << 'ENV'
# Base defaults
APP_NAME=myapp
PORT=8080
DATABASE_URL=postgresql://localhost:5432/myapp
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=info
SECRET_KEY=default-secret-change-me
FEATURE_FLAGS=none
DEBUG=false
API_TIMEOUT=30
ENV

cat > .env.production << 'ENV'
# Production configuration
APP_NAME=myapp
PORT=443
DATABASE_URL=postgresql://db.prod.internal:5432/myapp_prod
REDIS_URL=redis://redis.prod.internal:6379/0
LOG_LEVEL=warning
SECRET_KEY=prod-7f8a9b2c3d4e5f6a7b8c9d0e1f2a3b4c
FEATURE_FLAGS=stable-only
SENTRY_DSN=https://abc123@o456.ingest.sentry.io/789
ENV

cat > .env.local << 'ENV'
# Local developer overrides
APP_NAME=myapp
PORT=3000
DATABASE_URL=postgresql://localhost:5432/myapp_dev
LOG_LEVEL=debug
FEATURE_FLAGS=experimental,beta,stable
DEBUG=true
ENV

echo "Setup complete. Three .env files with conflicting values."
