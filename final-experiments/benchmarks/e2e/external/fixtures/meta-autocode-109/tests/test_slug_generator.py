import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from slug_generator import generate_slug

# PASS with bug (content is correct, just separator differs)

def test_lowercases():
    assert generate_slug('Hello').startswith('h')

def test_removes_special_chars():
    result = generate_slug('hello!')
    assert '!' not in result

def test_single_word_slug():
    assert generate_slug('python') == 'python'

def test_empty_returns_empty():
    assert generate_slug('') == ''

# FAIL with bug (hyphen expected, underscore produced)

def test_spaces_become_hyphens():
    assert generate_slug('hello world') == 'hello-world'  # bug: 'hello_world'

def test_multi_word_slug():
    assert generate_slug('Open Source Project') == 'open-source-project'  # bug: underscore

def test_no_underscores_in_slug():
    result = generate_slug('one two three')
    assert '_' not in result  # bug: underscores present
