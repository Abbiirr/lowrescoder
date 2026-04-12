# Task: Remove Hardcoded Secrets from Source Code

## Objective

The application in `app/` has hardcoded API keys and passwords scattered across multiple source files. Extract all secrets to environment variables and ensure the code reads them from the environment at runtime.

## Requirements

1. No hardcoded API keys, passwords, or secret tokens remain in any `.py` source file.
2. An `.env` file exists with placeholder values for all secrets (not the actual secrets).
3. All source files read secrets from environment variables (e.g., `os.environ`, `os.getenv`).
4. The application still functions correctly when environment variables are set.
5. An `.env.example` file documents all required environment variables.

## Current State

- `app/config.py` — Contains a hardcoded `DATABASE_PASSWORD` and `SECRET_KEY`.
- `app/payments.py` — Contains a hardcoded Stripe API key.
- `app/notifications.py` — Contains a hardcoded SendGrid API key.
- `app/.env.example` — Template listing expected env vars (empty values).

## Files

- `app/` — the application with hardcoded secrets
