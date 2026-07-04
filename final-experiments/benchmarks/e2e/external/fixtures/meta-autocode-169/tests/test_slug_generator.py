import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from slug_generator import slugify

# PASS (no spaces — replace does nothing, bug and fix agree)

def test_empty():
    assert slugify('') == ''

def test_single_word():
    assert slugify('hello') == 'hello'

def test_already_lowercase():
    assert slugify('python') == 'python'

def test_uppercase_no_spaces():
    assert slugify('FastAPI') == 'fastapi'

# FAIL (has spaces — bug produces underscores, fix produces hyphens)

def test_two_words():
    assert slugify('hello world') == 'hello-world'  # bug: 'hello_world'

def test_three_words():
    assert slugify('foo bar baz') == 'foo-bar-baz'  # bug: 'foo_bar_baz'

def test_mixed_case_with_spaces():
    assert slugify('Hello World') == 'hello-world'  # bug: 'hello_world'
