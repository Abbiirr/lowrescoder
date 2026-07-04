def validate_flow_inputs(flow):
    """Validate a flow dict; return list of error strings."""
    errors = []
    if not flow.get('name'):
        errors.append('name is required')
    nodes = flow.get('nodes', [])
    # BUG: validates node count but not that nodes is actually a list
    if len(nodes) == 0:
        errors.append('flow must have at least one node')
    return errors
