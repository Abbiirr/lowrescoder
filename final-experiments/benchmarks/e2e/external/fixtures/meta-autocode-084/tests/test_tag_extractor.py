import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from tag_extractor import extract_tags

# PASS with bug (no hyphens needed)

def test_no_tags_returns_empty():
    assert extract_tags('hello world') == []

def test_simple_tag():
    assert extract_tags('#python is great') == ['python']

def test_multiple_tags():
    result = extract_tags('#python and #code')
    assert result == ['python', 'code']

def test_deduplicates_tags():
    result = extract_tags('#python #code #python')
    assert result == ['python', 'code']

# FAIL with bug (hyphen in tag not matched)

def test_hyphenated_tag():
    result = extract_tags('#open-source project')
    assert result == ['open-source']  # bug: returns ['open']

def test_hyphenated_tag_in_sentence():
    result = extract_tags('I love #self-hosted tools')
    assert 'self-hosted' in result  # bug: 'self' matched, not 'self-hosted'

def test_mixed_tags():
    result = extract_tags('#python #open-source #code')
    assert result == ['python', 'open-source', 'code']  # bug: ['python', 'open', 'code']
