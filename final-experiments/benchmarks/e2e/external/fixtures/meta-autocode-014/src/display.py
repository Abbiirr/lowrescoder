# Terminal display utilities — has a bug.
# This file exists to be fixed by the agent.


def truncate(text: str, max_len: int, suffix: str = "…") -> str:
    """Truncate text to at most max_len characters.

    If text fits within max_len, return it unchanged.
    If not, truncate and append suffix so the total length == max_len.

    Bug: the suffix is appended AFTER cutting to max_len, making the result
    max_len + len(suffix) characters long — overflowing the display column.

    Fix: cut to max_len - len(suffix) before appending the suffix.
    """
    if len(text) <= max_len:
        return text
    # BUG: cuts to max_len then appends suffix → total > max_len
    return text[:max_len] + suffix


def pad_or_truncate(text: str, width: int) -> str:
    """Fit text into exactly `width` characters (truncate or right-pad with spaces)."""
    if len(text) >= width:
        return truncate(text, width)
    return text.ljust(width)
