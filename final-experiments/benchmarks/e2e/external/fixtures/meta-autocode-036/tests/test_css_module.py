import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from css_module import generate_css_module_class

def test_deterministic():
    a = generate_css_module_class("Button.module.css", "title")
    b = generate_css_module_class("Button.module.css", "title")
    assert a == b

def test_output_format():
    result = generate_css_module_class("Card.module.css", "body")
    assert result.startswith("body_")

def test_different_classes_same_file_unique():
    a = generate_css_module_class("Page.module.css", "title")
    b = generate_css_module_class("Page.module.css", "body")
    assert a != b

def test_result_nonempty():
    result = generate_css_module_class("App.module.css", "container")
    assert len(result) > 0

def test_collision_title_across_files():
    # BUG: both hash only 'title' → same result → collision
    a = generate_css_module_class("Button.module.css", "title")
    b = generate_css_module_class("Header.module.css", "title")
    assert a != b

def test_collision_name_across_files():
    # BUG: both hash only 'name' → collision
    a = generate_css_module_class("Card.module.css", "name")
    b = generate_css_module_class("List.module.css", "name")
    assert a != b

def test_collision_wrapper_across_files():
    # BUG: both hash only 'wrapper' → collision
    a = generate_css_module_class("Modal.module.css", "wrapper")
    b = generate_css_module_class("Sidebar.module.css", "wrapper")
    assert a != b
