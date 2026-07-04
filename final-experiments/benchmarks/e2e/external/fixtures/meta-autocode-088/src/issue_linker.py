import re

def extract_issue_refs(text):
    """Extract issue numbers from text like 'Fixes #123, relates to #456'."""
    # BUG: pattern requires 'Fixes' keyword; misses 'Closes', 'Resolves', 'Fix'
    return [int(m) for m in re.findall(r'(?:Fixes)\s+#(\d+)', text, re.IGNORECASE)]
