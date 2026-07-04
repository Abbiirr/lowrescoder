def validate_output_ports(ports):
    """Validate component output ports; return list of error strings."""
    errors = []
    # BUG: no duplicate name check — duplicate ports cause silent connection failures
    for port in ports:
        if not port.get('name'):
            errors.append('Port missing name')
    return errors
