import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from markdown_stripper import strip_markdown

# PASS with bug (bold/italic correctly stripped)

def test_strips_bold():
    assert strip_markdown('**hello**') == 'hello'

def test_strips_italic():
    assert strip_markdown('*world*') == 'world'

def test_strips_alt_bold():
    assert strip_markdown('__text__') == 'text'

def test_plain_text_unchanged():
    assert strip_markdown('hello world') == 'hello world'

# FAIL with bug (backticks not removed)

def test_strips_inline_code():
    assert strip_markdown('use `print()` function') == 'use print() function'  # bug: backticks stay

def test_strips_code_only():
    assert strip_markdown('`code`') == 'code'  # bug: '`code`'

def test_strips_mixed_code_bold():
    result = strip_markdown('**bold** and `code`')
    assert '`' not in result  # bug: backticks remain
