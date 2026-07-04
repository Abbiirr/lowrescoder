import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from text_chunker import split_into_chunks

# PASS (text length evenly divisible by size — last chunk never cut off)

def test_even_split():
    assert split_into_chunks('abcd', 2) == ['ab', 'cd']

def test_empty():
    assert split_into_chunks('', 2) == []

def test_three_chunks():
    assert split_into_chunks('abcdef', 2) == ['ab', 'cd', 'ef']

def test_size_three_even():
    assert split_into_chunks('abcdef', 3) == ['abc', 'def']

# FAIL (remainder is exactly 1 char — bug drops last chunk)

def test_odd_length():
    assert split_into_chunks('abcde', 2) == ['ab', 'cd', 'e']  # bug: ['ab', 'cd']

def test_longer_odd():
    assert split_into_chunks('abcdefg', 2) == ['ab', 'cd', 'ef', 'g']  # bug: ['ab','cd','ef']

def test_size_four_remainder_one():
    assert split_into_chunks('abcde', 4) == ['abcd', 'e']  # bug: ['abcd']
