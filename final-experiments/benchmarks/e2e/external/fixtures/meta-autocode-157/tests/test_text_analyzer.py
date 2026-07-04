import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from text_analyzer import count_vowels

# PASS (first char is consonant — skipping it doesn't change count)

def test_empty_string():
    assert count_vowels('') == 0

def test_starts_with_consonant():
    assert count_vowels('hello') == 2  # e, o — 'h' is consonant, both count same

def test_python():
    assert count_vowels('python') == 1  # o only — 'p' is consonant

def test_star():
    assert count_vowels('star') == 1  # a only — 's' is consonant

# FAIL (first char is a vowel — bug misses it)

def test_apple():
    assert count_vowels('apple') == 2  # a,e — bug: skips 'a', counts only e → 1

def test_ocean():
    assert count_vowels('ocean') == 3  # o,e,a — bug: skips 'o', counts e,a → 2

def test_air():
    assert count_vowels('air') == 2  # a,i — bug: skips 'a', counts i → 1
