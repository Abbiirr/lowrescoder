import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from search_indexer import build_index

# PASS with bug (words appear in only one document)

def test_empty_documents():
    assert build_index([]) == {}

def test_single_document():
    docs = [{'id': 1, 'content': 'hello world'}]
    index = build_index(docs)
    assert 1 in index.get('hello', [])

def test_unique_words_per_doc():
    docs = [
        {'id': 1, 'content': 'alpha'},
        {'id': 2, 'content': 'beta'},
    ]
    index = build_index(docs)
    assert index.get('alpha') == [1]
    assert index.get('beta') == [2]

def test_case_insensitive():
    docs = [{'id': 1, 'content': 'Hello WORLD'}]
    index = build_index(docs)
    assert 1 in index.get('hello', [])

# FAIL with bug (same word in multiple docs — overwrite loses earlier docs)

def test_word_in_multiple_docs():
    docs = [
        {'id': 1, 'content': 'python'},
        {'id': 2, 'content': 'python'},
    ]
    index = build_index(docs)
    assert 1 in index['python'] and 2 in index['python']  # bug: only [2]

def test_shared_word_all_docs_indexed():
    docs = [{'id': i, 'content': 'common word'} for i in range(3)]
    index = build_index(docs)
    assert len(index.get('common', [])) == 3  # bug: only [2]

def test_partial_shared_word():
    docs = [
        {'id': 10, 'content': 'foo bar'},
        {'id': 20, 'content': 'foo baz'},
    ]
    index = build_index(docs)
    assert 10 in index['foo']  # bug: index['foo'] == [20] only
