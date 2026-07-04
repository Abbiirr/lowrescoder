# Task: Resolve Conflicting .env Files

## Objective

Three `.env` files have conflicting values. Merge them according to the precedence rules below so the application gets the correct configuration.

## Precedence Rules (highest to lowest)

1. `.env.local` — Developer overrides. Highest priority.
2. `.env.production` — Production-specific values. Used if `.env.local` does not define the key.
3. `.env` — Base defaults. Used if neither of the above define the key.

## Requirements

1. Create a file called `resolved.env` containing the final merged configuration.
2. For keys present in multiple files, use the highest-precedence value per the rules above.
3. All keys from all three files must appear in `resolved.env`.
4. The `resolved.env` file must use `KEY=value` format, one entry per line (comments allowed).
5. Do NOT delete or modify the original `.env`, `.env.local`, or `.env.production` files.
6. The key order does not matter, but all keys must be present.

## Expected Key Sources (for verification)

| Key | Should come from | Reason |
|-----|-----------------|--------|
| `APP_NAME` | `.env` | Same in all files |
| `PORT` | `.env.local` | Override: dev uses 3000 |
| `DATABASE_URL` | `.env.local` | Override: dev uses localhost |
| `REDIS_URL` | `.env.production` | Not in .env.local, prod value preferred |
| `LOG_LEVEL` | `.env.local` | Override: dev uses debug |
| `SECRET_KEY` | `.env.production` | Not in .env.local, prod value preferred |
| `FEATURE_FLAGS` | `.env.local` | Override: dev enables experimental |
| `SENTRY_DSN` | `.env.production` | Only in production |
| `DEBUG` | `.env.local` | Override: dev enables debug |
| `API_TIMEOUT` | `.env` | Only in base defaults |

## Files

- `.env` — Base defaults
- `.env.local` — Developer overrides
- `.env.production` — Production values
