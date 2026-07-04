import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from theme_sorter import list_themes

def test_empty_list():
    assert list_themes([]) == []

def test_single_theme():
    assert list_themes(['Dracula']) == ['Dracula']

def test_all_lowercase():
    assert list_themes(['monokai', 'gruvbox', 'abyss']) == ['abyss', 'gruvbox', 'monokai']

def test_all_uppercase():
    assert list_themes(['NORD', 'DRACULA', 'ANT']) == ['ANT', 'DRACULA', 'NORD']

def test_uppercase_interspersed():
    # BUG: 'Monokai' (M=77) sorts before 'abyss' (a=97) with case-sensitive sort
    # Expected case-insensitive: ['abyss', 'Monokai', 'zenburn']
    assert list_themes(['zenburn', 'Monokai', 'abyss']) == ['abyss', 'Monokai', 'zenburn']

def test_capital_before_lowercase_bug():
    # BUG: ['Zenburn', 'abyss'] with case-sensitive (Z < a in ASCII)
    # Expected: ['abyss', 'Zenburn']
    assert list_themes(['Zenburn', 'abyss']) == ['abyss', 'Zenburn']

def test_mixed_case_full_list():
    # BUG: case-sensitive gives ['Dracula','Nord','gruvbox'] (D,N < g in ASCII)
    # Expected case-insensitive: ['Dracula', 'gruvbox', 'Nord']
    assert list_themes(['gruvbox', 'Dracula', 'Nord']) == ['Dracula', 'gruvbox', 'Nord']
