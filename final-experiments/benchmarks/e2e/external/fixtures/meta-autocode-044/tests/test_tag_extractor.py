import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from tag_extractor import extract_tags_from_memo

def test_single_line_tags():
    assert extract_tags_from_memo('#python #rust on one line') == ['python', 'rust']

def test_no_tags():
    assert extract_tags_from_memo('just text, no tags') == []

def test_empty_content():
    assert extract_tags_from_memo('') == []

def test_tag_on_first_line_only():
    assert extract_tags_from_memo('#todo\nsecond line') == ['todo']

def test_tag_on_second_line():
    # BUG: only first line processed — 'first\n#python' → [] instead of ['python']
    assert extract_tags_from_memo('first line\n#python') == ['python']

def test_tags_split_across_lines():
    # BUG: only '#a' captured, '#b' on line 2 missed
    assert extract_tags_from_memo('#a\n#b') == ['a', 'b']

def test_tag_only_on_last_line():
    # BUG: first line is 'text', no tag — but '#last' is on line 2, missed
    assert extract_tags_from_memo('text here\nmore text\n#last') == ['last']
