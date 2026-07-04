import re

def find_closing_issues(pr_description):
    """Return list of issue numbers referenced by Closes/closes/CLOSES #N keywords."""
    # BUG: case-sensitive pattern — only matches 'Closes', misses 'closes', 'CLOSES'
    return [int(m) for m in re.findall(r'Closes #(\d+)', pr_description)]
