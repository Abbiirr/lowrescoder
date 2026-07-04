import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from request_merger import merge_request_headers

# PASS with bug (Content-Type is application/json in these cases)

def test_request_header_overrides_base():
    base = {'Accept': 'application/json', 'X-Token': 'abc'}
    req = {'X-Token': 'xyz'}
    result = merge_request_headers(base, req)
    assert result['X-Token'] == 'xyz'

def test_base_header_preserved_when_not_overridden():
    base = {'Accept': 'application/json'}
    req = {'X-Token': 'xyz'}
    result = merge_request_headers(base, req)
    assert result['Accept'] == 'application/json'

def test_returns_dict():
    assert isinstance(merge_request_headers({}, {}), dict)

def test_default_content_type_set():
    result = merge_request_headers({}, {})
    assert result['Content-Type'] == 'application/json'

# FAIL with bug (Content-Type overwritten even when caller sets it)

def test_caller_content_type_preserved():
    base = {'Content-Type': 'text/plain'}
    req = {'X-Custom': 'val'}
    result = merge_request_headers(base, req)
    assert result['Content-Type'] == 'text/plain'  # bug: 'application/json'

def test_request_content_type_preserved():
    base = {}
    req = {'Content-Type': 'multipart/form-data'}
    result = merge_request_headers(base, req)
    assert result['Content-Type'] == 'multipart/form-data'  # bug: 'application/json'

def test_xml_content_type_not_overwritten():
    base = {'Content-Type': 'application/xml'}
    req = {}
    result = merge_request_headers(base, req)
    assert result['Content-Type'] == 'application/xml'  # bug: 'application/json'
