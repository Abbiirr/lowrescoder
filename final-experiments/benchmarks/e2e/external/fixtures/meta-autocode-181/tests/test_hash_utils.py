import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from hash_utils import short_hash

# PASS (hash shorter than 7 chars — both truncate to full string)

def test_empty():
    assert short_hash('') == ''

def test_three_chars():
    assert short_hash('abc') == 'abc'

def test_six_chars():
    assert short_hash('ab12cd') == 'ab12cd'

def test_one_char():
    assert short_hash('x') == 'x'

# FAIL (hash 7+ chars — bug returns 6 chars, fix returns 7)

def test_seven_chars():
    assert short_hash('abcdefg') == 'abcdefg'  # bug: 'abcdef'

def test_twelve_chars():
    assert short_hash('a1b2c3d4e5f6') == 'a1b2c3d'  # bug: 'a1b2c3'

def test_full_hash():
    assert short_hash('0123456789abcdef0123456789abcdef01234567') == '0123456'  # bug: '012345'
