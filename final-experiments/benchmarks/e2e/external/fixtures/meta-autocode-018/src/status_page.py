"""Status page monitor group sorting — inspired by louislam/uptime-kuma."""


def sort_monitor_groups(groups: list) -> list:
    """Sort monitor groups alphabetically for display on the status page.

    Args:
        groups: list of dicts, each with at least a "name" key

    Returns:
        groups sorted alphabetically by name (case-insensitive)
    """
    # BUG: case-sensitive sort puts uppercase names before all lowercase names
    return sorted(groups, key=lambda g: g["name"])
