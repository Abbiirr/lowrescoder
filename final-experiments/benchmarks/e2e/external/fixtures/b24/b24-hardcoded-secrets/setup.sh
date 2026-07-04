#!/usr/bin/env bash
set -euo pipefail

pip install pytest > /dev/null 2>&1

mkdir -p app
cd app

# Config with hardcoded secrets
cat > config.py << 'PY'
import os

APP_NAME = "myapp"
DEBUG = False

# Database configuration
DATABASE_HOST = "localhost"
DATABASE_PORT = 5432
DATABASE_NAME = "myapp_production"
DATABASE_PASSWORD = "sup3r_s3cret_db_passw0rd!"

# Application secret key for sessions
SECRET_KEY = "a1b2c3d4e5f6g7h8i9j0-flask-secret-key-do-not-share"

def get_database_url():
    return f"postgresql://admin:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

def get_secret_key():
    return SECRET_KEY
PY

# Payments module with hardcoded Stripe key
cat > payments.py << 'PY'
import json

STRIPE_API_KEY = "sk_live_4eC39HqLyjWDarjtT1zdp7dc_REAL_KEY"

class PaymentProcessor:
    def __init__(self):
        self.api_key = STRIPE_API_KEY

    def charge(self, amount_cents, currency="usd"):
        """Process a payment charge."""
        # In real code this would call Stripe API
        return {
            "status": "success",
            "amount": amount_cents,
            "currency": currency,
            "key_prefix": self.api_key[:7],
        }

    def refund(self, charge_id):
        """Process a refund."""
        return {"status": "refunded", "charge_id": charge_id}
PY

# Notifications module with hardcoded SendGrid key
cat > notifications.py << 'PY'
SENDGRID_API_KEY = "SG.aBcDeFgHiJkLmNoPqRsTuV.WxYz0123456789-real-sendgrid-key"

class EmailNotifier:
    def __init__(self):
        self.api_key = SENDGRID_API_KEY

    def send_email(self, to, subject, body):
        """Send an email notification."""
        # In real code this would call SendGrid API
        return {
            "status": "sent",
            "to": to,
            "subject": subject,
            "key_set": bool(self.api_key),
        }
PY

# .env.example template
cat > .env.example << 'ENV'
DATABASE_PASSWORD=
SECRET_KEY=
STRIPE_API_KEY=
SENDGRID_API_KEY=
ENV

# Tests
cat > test_app.py << 'PY'
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(__file__))

def test_config_database_url():
    """Config must produce a database URL."""
    # Set env vars so the module can load
    os.environ.setdefault("DATABASE_PASSWORD", "testpass")
    os.environ.setdefault("SECRET_KEY", "testkey")
    os.environ.setdefault("STRIPE_API_KEY", "sk_test_fake")
    os.environ.setdefault("SENDGRID_API_KEY", "SG.fake")

    # Reload modules to pick up env vars
    import importlib
    import config
    importlib.reload(config)

    url = config.get_database_url()
    assert "localhost" in url
    assert "myapp_production" in url

def test_config_secret_key():
    os.environ.setdefault("SECRET_KEY", "testkey")
    import importlib, config
    importlib.reload(config)
    key = config.get_secret_key()
    assert key is not None and len(key) > 0

def test_payment_charge():
    os.environ.setdefault("STRIPE_API_KEY", "sk_test_fake")
    import importlib, payments
    importlib.reload(payments)
    proc = payments.PaymentProcessor()
    result = proc.charge(1000)
    assert result["status"] == "success"
    assert result["amount"] == 1000

def test_payment_refund():
    os.environ.setdefault("STRIPE_API_KEY", "sk_test_fake")
    import importlib, payments
    importlib.reload(payments)
    proc = payments.PaymentProcessor()
    result = proc.refund("ch_123")
    assert result["status"] == "refunded"

def test_email_send():
    os.environ.setdefault("SENDGRID_API_KEY", "SG.fake")
    import importlib, notifications
    importlib.reload(notifications)
    notifier = notifications.EmailNotifier()
    result = notifier.send_email("bob@example.com", "Hello", "Test body")
    assert result["status"] == "sent"
    assert result["to"] == "bob@example.com"
PY

echo "Setup complete. Application with hardcoded secrets is ready in app/."
