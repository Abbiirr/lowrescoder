import re

def strip_markdown(text):
    """Remove common markdown formatting from text."""
    # BUG: strips bold/italic but leaves code backticks
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)        # italic
    text = re.sub(r'__(.+?)__', r'\1', text)         # bold alt
    # BUG: missing backtick removal
    return text
