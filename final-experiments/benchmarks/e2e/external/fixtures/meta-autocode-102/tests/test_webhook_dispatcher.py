import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from webhook_dispatcher import should_dispatch_event

# PASS with bug (event matches OR subscribed is non-empty both give True)

def test_matching_event_dispatched():
    assert should_dispatch_event('push', ['push', 'pull_request']) is True

def test_empty_subscribed_no_dispatch():
    assert should_dispatch_event('push', []) is False  # bug: False (empty list is falsy) ✓

def test_multiple_subscribed_returns_true():
    assert should_dispatch_event('issue', ['push', 'issue']) is True

def test_returns_bool():
    assert isinstance(should_dispatch_event('push', ['push']), bool)

# FAIL with bug (non-empty subscribed that doesn't contain event → should be False)

def test_non_matching_event_not_dispatched():
    assert should_dispatch_event('star', ['push', 'pull_request']) is False  # bug: True

def test_unsubscribed_event_blocked():
    assert should_dispatch_event('deploy', ['push']) is False  # bug: True

def test_wrong_event_type_blocked():
    assert should_dispatch_event('delete', ['create', 'update']) is False  # bug: True
