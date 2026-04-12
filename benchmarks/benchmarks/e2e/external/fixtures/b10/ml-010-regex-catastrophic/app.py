"""Input validation with regex patterns.

Bug: the email validation regex has catastrophic backtracking.
On certain inputs, the regex engine takes exponential time.
"""
import re


def validate_email(email):
    """Validate an email address using regex.

    Bug: the pattern (\\w+\\.?)+@ causes catastrophic backtracking on inputs
    like 'aaaaaaaaaaaaaaaaaaaaaaaaa!' because the engine tries exponentially
    many ways to match \\w+ and \\.? combinations before failing.

    Fix: use a non-backtracking pattern like [\\w.]+ or \\w+(?:\\.\\w+)*
    """
    # Bug: catastrophic backtracking pattern
    pattern = r"^(\w+\.?)+@(\w+\.)+\w{2,}$"
    return bool(re.match(pattern, email))


def validate_url(url):
    """Validate a URL format.

    Bug: similar catastrophic backtracking with nested quantifiers.
    Pattern (\\w+\\/?)+ causes exponential backtracking on non-matching input.
    """
    # Bug: catastrophic backtracking pattern
    pattern = r"^https?://(\w+/?)+\.\w{2,}(/\S*)?$"
    return bool(re.match(pattern, url))


def extract_tags(text):
    """Extract hashtags from text. This one is fine (no bug)."""
    return re.findall(r"#(\w+)", text)


def sanitize_input(text):
    """Remove non-alphanumeric characters except spaces. No bug here."""
    return re.sub(r"[^a-zA-Z0-9 ]", "", text)
