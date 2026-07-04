import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from memo_summarizer import summarize_memo

# PASS (fewer words than max_words — both return all words)

def test_two_words():
    assert summarize_memo('hello world') == 'hello world'

def test_four_words():
    assert summarize_memo('a b c d') == 'a b c d'

def test_empty():
    assert summarize_memo('') == ''

def test_three_words():
    assert summarize_memo('one two three') == 'one two three'

# FAIL (words >= max_words=5 — bug returns one fewer word)

def test_exactly_five_words():
    assert summarize_memo('a b c d e') == 'a b c d e'  # bug: 'a b c d'

def test_six_words():
    assert summarize_memo('one two three four five six') == 'one two three four five'  # bug: 'one two three four'

def test_seven_words():
    assert summarize_memo('w1 w2 w3 w4 w5 w6 w7') == 'w1 w2 w3 w4 w5'  # bug: 'w1 w2 w3 w4'
