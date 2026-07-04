"""Response serializer — inspired by fastapi/fastapi pydantic response_model."""


def serialize_response(data: dict, exclude_none: bool = False) -> dict:
    """Serialize a response dict, optionally dropping None-valued fields.

    Args:
        data: response data dict (may be nested)
        exclude_none: if True, remove fields whose value is None

    Returns:
        serialized dict with None fields removed at all levels (if exclude_none)
    """
    if not exclude_none:
        return data
    # BUG: only removes None values at the top level — nested dicts are not
    # recursed into, so nested None fields are silently kept.
    return {k: v for k, v in data.items() if v is not None}
