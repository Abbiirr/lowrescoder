def serialize_response(data, exclude_none=False):
    """Serialize a dict response, optionally stripping None values."""
    if isinstance(data, dict):
        # BUG: ignores exclude_none — always includes None values
        return {k: v for k, v in data.items()}
    return data
