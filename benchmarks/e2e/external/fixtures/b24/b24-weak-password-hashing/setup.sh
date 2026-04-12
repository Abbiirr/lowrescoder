#!/usr/bin/env bash
set -euo pipefail

pip install pytest bcrypt > /dev/null 2>&1

mkdir -p app
cd app

# Authentication module with weak MD5 hashing
cat > auth.py << 'PY'
import hashlib
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def get_db(db_path=None):
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    db = get_db(db_path)
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()
    db.close()

def hash_password(password):
    """Hash a password. INSECURE: uses MD5."""
    return hashlib.md5(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify a password against its hash."""
    return hash_password(password) == password_hash

def create_user(username, password, db_path=None):
    """Create a new user with hashed password."""
    db = get_db(db_path)
    pw_hash = hash_password(password)
    try:
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, pw_hash),
        )
        db.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        db.close()

def authenticate(username, password, db_path=None):
    """Authenticate a user. Returns user row or None."""
    db = get_db(db_path)
    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    db.close()

    if user and verify_password(password, user["password_hash"]):
        return dict(user)
    return None
PY

# Test file
cat > test_app.py << 'PY'
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import auth

@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    db_path = str(tmp_path / "test_users.db")
    auth.DB_PATH = db_path
    auth.init_db(db_path)
    yield db_path

def test_hash_password():
    """Hashing the same password twice should produce consistent results."""
    h1 = auth.hash_password("mypassword")
    h2 = auth.hash_password("mypassword")
    # Note: with bcrypt/argon2, hashes will differ but verify should work
    # This test just checks that hash_password returns something
    assert h1 is not None
    assert len(h1) > 0

def test_verify_password():
    """Correct password should verify, wrong password should not."""
    pw_hash = auth.hash_password("correctpassword")
    assert auth.verify_password("correctpassword", pw_hash) is True
    assert auth.verify_password("wrongpassword", pw_hash) is False

def test_create_user(setup_db):
    """Should create a user successfully."""
    result = auth.create_user("alice", "password123", setup_db)
    assert result is True

def test_create_duplicate_user(setup_db):
    """Duplicate username should fail."""
    auth.create_user("bob", "pass1", setup_db)
    result = auth.create_user("bob", "pass2", setup_db)
    assert result is False

def test_authenticate_valid(setup_db):
    """Valid credentials should authenticate."""
    auth.create_user("charlie", "secret", setup_db)
    user = auth.authenticate("charlie", "secret", setup_db)
    assert user is not None
    assert user["username"] == "charlie"

def test_authenticate_wrong_password(setup_db):
    """Wrong password should fail authentication."""
    auth.create_user("dave", "realpass", setup_db)
    user = auth.authenticate("dave", "fakepass", setup_db)
    assert user is None

def test_authenticate_nonexistent_user(setup_db):
    """Nonexistent user should fail authentication."""
    user = auth.authenticate("nobody", "anything", setup_db)
    assert user is None

def test_different_passwords_different_hashes():
    """Different passwords should produce different hashes (or at least verify differently)."""
    h1 = auth.hash_password("password1")
    h2 = auth.hash_password("password2")
    # With salted hashing, same password gives different hashes,
    # so we just check they exist and verify works
    assert auth.verify_password("password1", h1) is True
    assert auth.verify_password("password2", h2) is True
    assert auth.verify_password("password1", h2) is False
PY

# Initialize DB
python -c "import auth; auth.init_db()"

echo "Setup complete. Auth module with weak MD5 password hashing is ready in app/."
