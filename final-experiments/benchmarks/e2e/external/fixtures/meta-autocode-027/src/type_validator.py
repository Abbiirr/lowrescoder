"""Langflow node connection type validator — inspired by langflow-ai/langflow."""


def can_connect(output_type, input_type):
    """Return True if a node output of output_type can connect to an input of input_type.

    'Any' acts as a wildcard that accepts or provides any type.
    """
    # BUG: exact match only — doesn't treat 'Any' as a wildcard
    return output_type == input_type
