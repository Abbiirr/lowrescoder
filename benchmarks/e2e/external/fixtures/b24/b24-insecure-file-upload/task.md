# Task: Secure the File Upload Endpoint

## Objective

The Flask app in `app/` has an insecure file upload endpoint that accepts any file type and stores files in a publicly accessible directory with the original filename. Fix the security issues while keeping file upload functionality working.

## Requirements

1. **File type validation** — Only allow specific safe file types (e.g., `.png`, `.jpg`, `.jpeg`, `.gif`, `.pdf`, `.txt`). Reject dangerous types like `.py`, `.sh`, `.exe`, `.php`, `.js`.
2. **Secure storage** — Files must be stored outside the public/static directory (e.g., in an `uploads/` directory that is not web-accessible).
3. **Filename sanitization** — The stored filename must be sanitized (no path traversal, no special characters). Use `werkzeug.utils.secure_filename` or equivalent.
4. **All existing tests must pass** (`python -m pytest test_app.py`).

## Current State

- `app/app.py` — Flask application with a `/upload` POST endpoint that saves any uploaded file directly to `static/uploads/` with the original filename.
- `app/test_app.py` — Tests for the upload endpoint.
- `app/static/uploads/` — Public upload directory (insecure).

## Files

- `app/` — the vulnerable Flask application
