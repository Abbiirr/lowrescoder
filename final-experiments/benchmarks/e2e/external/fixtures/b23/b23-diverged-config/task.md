# Task: Reconcile Diverged Dev and Prod Config Files

## Objective

The `dev.env` and `prod.env` configuration files have diverged. Some keys are missing from one or the other, and the files need to be reconciled so both environments have all required keys.

## Requirements

1. Both `dev.env` and `prod.env` must contain ALL of the following keys:
   - `APP_NAME`, `APP_PORT`, `DATABASE_URL`, `DATABASE_POOL_SIZE`, `REDIS_URL`, `LOG_LEVEL`, `CORS_ORIGINS`, `SECRET_KEY`, `FEATURE_NEW_UI`, `SENTRY_DSN`
2. `prod.env` must have production-appropriate values:
   - `LOG_LEVEL` must be `warning` or `error` (not `debug`)
   - `CORS_ORIGINS` must NOT contain `localhost`
   - `SECRET_KEY` must NOT be `dev-secret-key-123` or contain `dev`
   - `FEATURE_NEW_UI` must be `false` (not yet released to prod)
3. `dev.env` must have development-appropriate values:
   - `LOG_LEVEL` must be `debug`
   - `DATABASE_URL` must contain `localhost`
4. Values that already exist and are environment-appropriate should not be changed.
5. Both files must use `KEY=value` format, one per line. Comments (`#`) are allowed.

## Current State

- `dev.env` — Missing `SENTRY_DSN`, `FEATURE_NEW_UI`. Has 8 keys.
- `prod.env` — Missing `CORS_ORIGINS`, `REDIS_URL`, `FEATURE_NEW_UI`. Has 7 keys. Also has `LOG_LEVEL=debug` which is wrong for prod.

## Files

- `dev.env` — Development config to fix
- `prod.env` — Production config to fix
