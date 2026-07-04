"""Terminal display width calculator — inspired by sharkdp/bat."""


def display_width(text: str, tab_width: int = 4) -> int:
    """Return the terminal display width of text, expanding tabs to tab stops.

    Tabs advance to the next multiple of tab_width columns (1-indexed stops).

    Args:
        text: input string (may contain tabs)
        tab_width: number of columns per tab stop (default 4)

    Returns:
        display width in terminal columns
    """
    # BUG: counts each character (including \\t) as width 1.
    # Tabs must be expanded to the next tab stop, not counted as one column.
    return len(text)
