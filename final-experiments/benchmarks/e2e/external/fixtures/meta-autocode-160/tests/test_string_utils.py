import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from string_utils import is_palindrome

# PASS (all lowercase — bug and fix agree)

def test_lowercase_palindrome():
    assert is_palindrome('racecar') == True

def test_not_palindrome():
    assert is_palindrome('hello') == False

def test_numeric_palindrome():
    assert is_palindrome('121') == True

def test_not_palindrome_word():
    assert is_palindrome('python') == False

# FAIL (mixed case — bug: case-sensitive comparison fails, fix: True)

def test_mixed_case_racecar():
    assert is_palindrome('Racecar') == True  # bug: 'Racecar' != 'racecaR' → False

def test_mixed_case_madam():
    assert is_palindrome('Madam') == True  # bug: 'Madam' != 'madaM' → False

def test_mixed_case_level():
    assert is_palindrome('Level') == True  # bug: 'Level' != 'leveL' → False
