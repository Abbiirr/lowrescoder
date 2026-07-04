def is_port_available(port, used_ports):
    """Return True if port is not already in use."""
    # BUG: logic is inverted — returns True when port IS used
    return port in used_ports
