#!/usr/bin/env bash
set -euo pipefail

cat > dev.env << 'ENV'
# Development environment config
APP_NAME=myapp
APP_PORT=3000
DATABASE_URL=postgresql://localhost:5432/myapp_dev
DATABASE_POOL_SIZE=5
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=debug
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
SECRET_KEY=dev-secret-key-123
ENV

cat > prod.env << 'ENV'
# Production environment config
APP_NAME=myapp
APP_PORT=8080
DATABASE_URL=postgresql://db.prod.internal:5432/myapp
DATABASE_POOL_SIZE=20
LOG_LEVEL=debug
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0
SENTRY_DSN=https://abc123@sentry.io/456
ENV

echo "Setup complete. dev.env and prod.env have diverged."
