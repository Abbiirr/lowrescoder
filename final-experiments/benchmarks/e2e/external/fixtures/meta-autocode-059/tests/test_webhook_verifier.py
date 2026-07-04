import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from webhook_verifier import verify_webhook_signature

# Pre-computed HMAC values for payload='test-payload', secret='webhook-secret':
# SHA1:   a540ccc52d4e9513cab941781c0d4a0f3425cfa2
# SHA256: 55c4ef30455579ddb93590f757f42c068ec59a0147a97494a2b6bd246c2cc782

# --- PASS with bug (wrong signature → both return False) ---

def test_tampered_payload_rejected():
    sig = '55c4ef30455579ddb93590f757f42c068ec59a0147a97494a2b6bd246c2cc782'
    assert verify_webhook_signature('tampered-payload', 'webhook-secret', sig) is False

def test_wrong_secret_rejected():
    sig = '55c4ef30455579ddb93590f757f42c068ec59a0147a97494a2b6bd246c2cc782'
    assert verify_webhook_signature('test-payload', 'wrong-secret', sig) is False

def test_empty_signature_rejected():
    assert verify_webhook_signature('test-payload', 'webhook-secret', '') is False

def test_sha1_sig_rejected_by_fix():
    # The SHA1 signature: bug would accept it, but we need a passing test.
    # Use with wrong payload so both bug and fix reject.
    sha1_sig = 'a540ccc52d4e9513cab941781c0d4a0f3425cfa2'
    assert verify_webhook_signature('different-payload', 'webhook-secret', sha1_sig) is False

# --- FAIL with bug (valid SHA256 sig: fix returns True, bug returns False) ---

def test_valid_sha256_signature():
    sig = '55c4ef30455579ddb93590f757f42c068ec59a0147a97494a2b6bd246c2cc782'
    assert verify_webhook_signature('test-payload', 'webhook-secret', sig) is True

def test_second_payload_sha256():
    # payload='event=push&repo=myrepo', secret='secret-key-abc'
    # SHA256: 2d5caba5695d4bcff7fd06f3959479ed3802dc20058c4db6685091dc336bd160
    sig = '2d5caba5695d4bcff7fd06f3959479ed3802dc20058c4db6685091dc336bd160'
    assert verify_webhook_signature('event=push&repo=myrepo', 'secret-key-abc', sig) is True

def test_sha1_sig_rejected_when_sha256_required():
    # SHA1 signature for test-payload/webhook-secret — fix should reject it
    sha1_sig = 'a540ccc52d4e9513cab941781c0d4a0f3425cfa2'
    # Bug: hmac matches SHA1 → True; Fix: expects SHA256 → False
    assert verify_webhook_signature('test-payload', 'webhook-secret', sha1_sig) is False
