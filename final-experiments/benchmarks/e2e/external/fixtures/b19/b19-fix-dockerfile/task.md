# Task: Fix a Broken Dockerfile

## Objective

The `Dockerfile` for a Python Flask application has several issues that prevent it from building correctly and following best practices. Fix all issues.

## Requirements

1. The Dockerfile must use a valid base image tag (`python:3.11-slim`, not a nonexistent tag).
2. A `WORKDIR` must be set before any `COPY` or `RUN` commands that reference application files.
3. System dependencies (`apt-get`) must be installed before application files are copied (layer caching best practice).
4. The Dockerfile must have valid syntax and follow standard ordering conventions.
5. The application must be runnable via the `CMD` instruction.

## Current Bugs

- Base image uses `python:3.11-ultraslim` which does not exist (should be `python:3.11-slim`)
- No `WORKDIR` is set — files are copied to root `/` which is bad practice
- `COPY . .` appears before `RUN apt-get update && apt-get install -y ...` — this breaks layer caching and may fail if system deps are needed for pip install

## Files

- `Dockerfile` — the broken Dockerfile
- `app.py` — simple Flask application
- `requirements.txt` — Python dependencies
