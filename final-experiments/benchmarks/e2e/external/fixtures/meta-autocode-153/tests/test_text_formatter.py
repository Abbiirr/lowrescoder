import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from text_formatter import to_title_case

# PASS (no apostrophes — title() and manual capitalize agree)

def test_empty_string():
    assert to_title_case('') == ''

def test_single_word():
    assert to_title_case('hello') == 'Hello'

def test_two_words():
    assert to_title_case('hello world') == 'Hello World'

def test_already_uppercase():
    assert to_title_case('FOO BAR') == 'Foo Bar'  # both: capitalize lowercases rest

# FAIL (apostrophes — title() wrongly uppercases letter after apostrophe)

def test_contraction_dont():
    assert to_title_case("don't stop") == "Don't Stop"  # bug: "Don'T Stop"

def test_contraction_its():
    assert to_title_case("it's alive") == "It's Alive"  # bug: "It'S Alive"

def test_contraction_weve():
    assert to_title_case("we've got this") == "We've Got This"  # bug: "We'Ve Got This"
