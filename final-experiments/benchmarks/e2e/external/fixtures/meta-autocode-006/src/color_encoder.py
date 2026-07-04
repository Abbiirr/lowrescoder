# Pydantic v2 color encoding — has a bug.
# This file exists to be fixed by the agent.

def encode_color(value):
    """Encode a color object to a string for JSON serialization.

    Should handle:
    - pydantic.v1.color.Color (legacy)
    - pydantic_extra_types.color.Color (modern)
    - plain strings (pass through)
    - None (return None)

    Current bug: raises AttributeError on pydantic_extra_types Color objects
    because it only tries the legacy .as_hex() method.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    # BUG: only handles legacy pydantic v1 Color, crashes on pydantic_extra_types Color
    return value.as_hex()
