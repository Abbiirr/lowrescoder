import json

def serialize_response(data, exclude_none=True):
    """Serialize data to JSON, optionally excluding None values."""
    if exclude_none:
        # BUG: only strips top-level None values, not nested
        cleaned = {k: v for k, v in data.items() if v is not None}
    else:
        cleaned = data
    return json.dumps(cleaned)
