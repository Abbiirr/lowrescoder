# Task: Fix a Half-Completed Deployment

## Objective

A deployment script crashed midway through updating a web application from v1 to v2. Some files have been updated, others are still on v1. Complete the deployment so all files are at v2.

## Requirements

1. `webapp/version.txt` must contain exactly `2.0`.
2. `webapp/app.py` must contain the v2 feature: the `/api/v2/health` endpoint.
3. `webapp/templates/index.html` must reference `v2.0` in its content.
4. `webapp/static/style.css` must contain the v2 theme (dark mode CSS).
5. All files must be internally consistent -- no mix of v1 and v2 references.
6. `webapp/deploy_manifest.json` already specifies that all files should be at v2 -- use it as the source of truth.

## Current State

- `webapp/` contains a mix of v1 and v2 files.
- `webapp/deploy_manifest.json` lists the expected v2 state of every file.
- `webapp/v2_bundle/` contains the v2 versions of all files (the deploy source).
- `webapp/version.txt` still says `1.0` (not yet updated).
- `webapp/app.py` has been updated to v2 already.
- `webapp/templates/index.html` is still v1.
- `webapp/static/style.css` is still v1.

## Files

- `webapp/` -- the web application in a partially deployed state
- `webapp/deploy_manifest.json` -- describes what v2 should look like
- `webapp/v2_bundle/` -- the v2 source files
