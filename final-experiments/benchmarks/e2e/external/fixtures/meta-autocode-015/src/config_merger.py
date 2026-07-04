# Config merge utility — has a bug.
# This file exists to be fixed by the agent.


def merge_config(base: dict, override: dict) -> dict:
    """Merge two config dicts, with override taking precedence.

    For nested dicts, keys in base that are NOT in override must be preserved.

    Bug: uses shallow dict unpacking — nested dicts in base are entirely
    replaced by the override value instead of being recursively merged.
    This causes sibling keys inside nested sections to vanish.

    Fix: recurse into nested dicts instead of replacing them.
    """
    # BUG: {**base, **override} replaces nested dicts wholesale
    return {**base, **override}
