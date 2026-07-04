def get_client_env_vars(env_vars):
    """Return only the env vars that should be exposed to the client (VITE_ prefix)."""
    # BUG: no prefix filter — exposes all env vars including secrets
    return env_vars.copy()
