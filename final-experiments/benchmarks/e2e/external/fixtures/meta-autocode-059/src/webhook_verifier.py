import hmac
import hashlib


def verify_webhook_signature(payload, secret, signature):
    """Verify HMAC-SHA256 webhook signature. Returns True if valid."""
    # BUG: uses SHA1 instead of SHA256
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha1).hexdigest()
    return hmac.compare_digest(expected, signature)
