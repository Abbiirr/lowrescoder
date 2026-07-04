# TASK-059: Fix Webhook Signature HMAC Algorithm (go-gitea/gitea pattern)

## Source
Inspired by go-gitea/gitea webhook delivery. Gitea signs payloads with
HMAC-SHA256. The bug uses SHA1 (`hashlib.sha1`), which produces incorrect
signatures and rejects valid SHA256-signed webhooks.

## Goal
Fix `src/webhook_verifier.py` so `verify_webhook_signature()` uses
`hashlib.sha256` instead of `hashlib.sha1`.

## The bug
```python
# BUG: wrong algorithm
expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha1).hexdigest()

# Fix: use SHA256
expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
```

## Failing tests (3/7 fail initially)
```
test_valid_sha256_signature        ← FAILS (valid SHA256 sig rejected by bug using SHA1)
test_second_payload_sha256         ← FAILS (another valid SHA256 sig rejected)
test_sha1_sig_rejected_when_sha256_required ← FAILS (bug accepts SHA1 sig, fix rejects it)
```
