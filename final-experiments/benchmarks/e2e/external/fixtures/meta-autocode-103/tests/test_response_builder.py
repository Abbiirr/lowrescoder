import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from response_builder import build_api_response

# PASS with bug

def test_200_is_success():
    r = build_api_response({'id': 1})
    assert r['success'] is True

def test_500_not_success():
    r = build_api_response(None, 500)
    assert r['success'] is False

def test_404_not_success():
    r = build_api_response(None, 404)
    assert r['success'] is False

def test_response_has_data():
    r = build_api_response('hello')
    assert r['data'] == 'hello'

# FAIL with bug (2xx codes other than 200 should be success)

def test_201_is_success():
    r = build_api_response({'id': 1}, 201)
    assert r['success'] is True  # bug: False

def test_204_is_success():
    r = build_api_response(None, 204)
    assert r['success'] is True  # bug: False

def test_202_is_success():
    r = build_api_response({'queued': True}, 202)
    assert r['success'] is True  # bug: False
