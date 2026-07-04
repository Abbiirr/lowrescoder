import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from port_validator import validate_output_ports

# --- PASS with bug (no duplicates, or missing-name detection agrees) ---

def test_valid_distinct_ports():
    ports = [{'name': 'output'}, {'name': 'debug'}]
    assert validate_output_ports(ports) == []

def test_empty_ports():
    assert validate_output_ports([]) == []

def test_single_port():
    assert validate_output_ports([{'name': 'out'}]) == []

def test_missing_name_detected():
    # Bug already detects missing names — both agree on this error
    ports = [{'name': ''}, {'name': 'ok'}]
    errors = validate_output_ports(ports)
    assert 'Port missing name' in errors

# --- FAIL with bug (duplicate names not caught) ---

def test_duplicate_port_names():
    ports = [{'name': 'result'}, {'name': 'result'}]
    errors = validate_output_ports(ports)
    assert any('Duplicate' in e or 'duplicate' in e for e in errors)

def test_duplicate_among_valid():
    ports = [{'name': 'a'}, {'name': 'b'}, {'name': 'a'}]
    errors = validate_output_ports(ports)
    assert len(errors) >= 1

def test_all_same_name():
    ports = [{'name': 'x'}, {'name': 'x'}, {'name': 'x'}]
    errors = validate_output_ports(ports)
    assert len(errors) >= 2
