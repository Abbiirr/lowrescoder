import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from config_validator import validate_config

# PASS with bug (None and missing keys correctly flagged; truthy values pass)

def test_no_required_keys():
    assert validate_config({'a': 1}, []) == []

def test_missing_key():
    assert validate_config({}, ['port']) == ['port']

def test_none_value_missing():
    assert validate_config({'port': None}, ['port']) == ['port']

def test_truthy_value_present():
    assert validate_config({'host': 'localhost', 'port': 8080}, ['host', 'port']) == []

# FAIL with bug (falsy non-None values flagged as missing)

def test_zero_is_valid():
    # port=0 is a valid (though unusual) value; bug marks it missing
    assert validate_config({'port': 0}, ['port']) == []  # bug: ['port']

def test_empty_string_is_missing():
    # Actually empty string IS missing — but we want to distinguish from None
    # Let's use False as a valid boolean flag
    assert validate_config({'enabled': False}, ['enabled']) == []  # bug: ['enabled']

def test_empty_list_is_valid():
    # An empty list is a valid value (e.g. allowed_hosts=[])
    assert validate_config({'allowed_hosts': []}, ['allowed_hosts']) == []  # bug: ['allowed_hosts']
