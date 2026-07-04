"""Vite-style config merger — inspired by vitejs/vite mergeConfig."""


def merge_vite_config(base, override):
    """Merge two vite config dicts. Dicts deep-merge; arrays should concatenate."""
    result = {}
    all_keys = set(list(base.keys()) + list(override.keys()))
    for key in all_keys:
        if key in base and key in override:
            if isinstance(base[key], dict) and isinstance(override[key], dict):
                result[key] = merge_vite_config(base[key], override[key])
            else:
                # BUG: arrays are replaced instead of concatenated
                result[key] = override[key]
        elif key in base:
            result[key] = base[key]
        else:
            result[key] = override[key]
    return result
