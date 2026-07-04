def is_js_file(filename):
    """Return True if filename has a JavaScript file extension."""
    # BUG: only checks .js — misses ESM (.mjs) and CommonJS (.cjs) variants
    return filename.endswith('.js')
