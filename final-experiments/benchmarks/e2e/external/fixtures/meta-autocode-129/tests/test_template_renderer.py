import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from template_renderer import render_template

# PASS with bug (single-brace templates work fine with the bug)

def test_empty_template():
    assert render_template('', {'name': 'Alice'}) == ''

def test_no_variables():
    assert render_template('Hello world', {}) == 'Hello world'

def test_single_brace_template():
    # Bug uses single braces — this test uses single braces too
    assert render_template('Hello {name}', {'name': 'Alice'}) == 'Hello Alice'

def test_multiple_single_brace():
    result = render_template('{greeting} {name}', {'greeting': 'Hi', 'name': 'Bob'})
    assert result == 'Hi Bob'

# FAIL with bug (double-brace templates not substituted)

def test_double_brace_template():
    result = render_template('Hello {{name}}', {'name': 'Alice'})
    assert result == 'Hello Alice'  # bug: 'Hello {{name}}' (no substitution)

def test_double_brace_multiple():
    result = render_template('{{greeting}}, {{name}}!', {'greeting': 'Hi', 'name': 'Bob'})
    assert result == 'Hi, Bob!'  # bug: '{{greeting}}, {{name}}!'

def test_double_brace_with_value():
    result = render_template('Count: {{count}}', {'count': 42})
    assert result == 'Count: 42'  # bug: 'Count: {{count}}'
