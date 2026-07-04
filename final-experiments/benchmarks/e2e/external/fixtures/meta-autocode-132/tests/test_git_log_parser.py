import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from git_log_parser import parse_commit_line

# PASS with bug (hash is always correct; author-only line works)

def test_invalid_line_returns_none():
    assert parse_commit_line('no-separator') is None

def test_hash_is_parsed():
    result = parse_commit_line('abc123|Alice|Fix bug')
    assert result['hash'] == 'abc123'

def test_two_part_line():
    # Only hash|author (no message) — bug and fix agree
    result = parse_commit_line('deadbeef|Bob')
    assert result is not None
    assert result['hash'] == 'deadbeef'

def test_whitespace_stripped():
    result = parse_commit_line('  abc  |  Alice  |  msg  ')
    assert result['hash'] == 'abc'

# FAIL with bug (author and message split at wrong index)

def test_author_is_parsed():
    result = parse_commit_line('abc123|Alice|Fix bug')
    # Bug: author = 'Alice|Fix bug' (split(|,1) gives only 2 parts)
    assert result['author'] == 'Alice'

def test_message_is_parsed():
    result = parse_commit_line('abc123|Alice|Fix bug')
    assert result['message'] == 'Fix bug'  # bug: message is ''

def test_message_with_pipe():
    # Message itself contains a pipe
    result = parse_commit_line('abc|Bob|Merge: a|b')
    assert result['author'] == 'Bob'
    assert result['message'] == 'Merge: a|b'
