import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from case_converter import camel_to_snake

# PASS (lowercase start — no leading uppercase, no leading underscore)

def test_empty():
    assert camel_to_snake('') == ''

def test_single_word():
    assert camel_to_snake('hello') == 'hello'

def test_camel_case():
    assert camel_to_snake('myVariable') == 'my_variable'

def test_multi_hump():
    assert camel_to_snake('fooBarBaz') == 'foo_bar_baz'

# FAIL (PascalCase — bug adds leading underscore)

def test_pascal_simple():
    assert camel_to_snake('MyClass') == 'my_class'  # bug: '_my_class'

def test_pascal_multi():
    assert camel_to_snake('PascalCase') == 'pascal_case'  # bug: '_pascal_case'

def test_pascal_acronym():
    assert camel_to_snake('HttpRequest') == 'http_request'  # bug: '_http_request'
