def get_node_inputs(node):
    """Return the list of input definitions for a langflow node."""
    # BUG: reads 'input' (singular) instead of 'inputs'
    return node.get('input', [])
