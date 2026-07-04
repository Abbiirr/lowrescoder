import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from component_validator import validate_component_metadata

# --- PASS with bug (name absent or both valid — both agree) ---

def test_valid_metadata():
    errors = validate_component_metadata({'name': 'Loader', 'description': 'Loads data'})
    assert errors == []

def test_missing_name_detected():
    errors = validate_component_metadata({'name': '', 'description': 'ok'})
    assert 'name is required' in errors

def test_none_name_detected():
    errors = validate_component_metadata({'name': None, 'description': 'ok'})
    assert 'name is required' in errors

def test_both_missing_name_still_detected():
    errors = validate_component_metadata({'name': '', 'description': ''})
    assert 'name is required' in errors

# --- FAIL with bug (description missing but name ok — bug silent, fix reports) ---

def test_empty_description_detected():
    errors = validate_component_metadata({'name': 'MyComp', 'description': ''})
    assert any('description' in e for e in errors)

def test_none_description_detected():
    errors = validate_component_metadata({'name': 'MyComp', 'description': None})
    assert any('description' in e for e in errors)

def test_missing_description_key_detected():
    errors = validate_component_metadata({'name': 'MyComp'})
    assert any('description' in e for e in errors)
