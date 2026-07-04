#!/usr/bin/env bash
set -euo pipefail

pip install sqlalchemy --quiet

cat > models.py << 'PY'
"""SQLAlchemy ORM models — this is the source of truth for schema."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    posts = relationship("Post", back_populates="author")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    author = relationship("User", back_populates="posts")
PY

cat > validate_models.py << 'PY'
"""Validate that DB schema matches ORM models. DO NOT MODIFY."""
import sys
from sqlalchemy import create_engine, inspect

# Expected schema from models
EXPECTED = {
    "users": {"id", "username", "email", "created_at"},
    "posts": {"id", "title", "content", "created_at", "updated_at", "author_id"},
}


def validate():
    engine = create_engine("sqlite:///app.db")
    inspector = inspect(engine)
    errors = []

    for table_name, expected_cols in EXPECTED.items():
        if table_name not in inspector.get_table_names():
            errors.append(f"Table '{table_name}' missing from database")
            continue

        actual_cols = {col["name"] for col in inspector.get_columns(table_name)}

        missing = expected_cols - actual_cols
        extra = actual_cols - expected_cols

        if missing:
            errors.append(f"Table '{table_name}' missing columns: {missing}")
        if extra:
            errors.append(f"Table '{table_name}' has extra columns: {extra}")

    # Check data preserved
    from sqlalchemy import text
    with engine.connect() as conn:
        user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        post_count = conn.execute(text("SELECT COUNT(*) FROM posts")).scalar()
        if user_count < 3:
            errors.append(f"Users table should have >= 3 rows, has {user_count}")
        if post_count < 4:
            errors.append(f"Posts table should have >= 4 rows, has {post_count}")

        # Check email column has values for existing users
        null_emails = conn.execute(text("SELECT COUNT(*) FROM users WHERE email IS NULL OR email = ''")).scalar()
        if null_emails > 0:
            errors.append(f"Users table has {null_emails} rows with null/empty email")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return False
    else:
        print("All validations passed")
        return True


if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
PY

# Create the DRIFTED database (not matching models)
python << 'PY'
import sqlite3

conn = sqlite3.connect("app.db")
c = conn.cursor()

# Users table: missing 'email', has extra 'legacy_role'
c.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        legacy_role VARCHAR(20) DEFAULT 'user',
        created_at DATETIME
    )
""")

# Posts table: missing 'updated_at', has extra 'view_count'
c.execute("""
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY,
        title VARCHAR(200) NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME,
        view_count INTEGER DEFAULT 0,
        author_id INTEGER NOT NULL REFERENCES users(id)
    )
""")

# Insert sample data
c.execute("INSERT INTO users (id, username, legacy_role, created_at) VALUES (1, 'alice', 'admin', '2024-01-15 10:00:00')")
c.execute("INSERT INTO users (id, username, legacy_role, created_at) VALUES (2, 'bob', 'user', '2024-02-20 14:30:00')")
c.execute("INSERT INTO users (id, username, legacy_role, created_at) VALUES (3, 'charlie', 'user', '2024-03-10 09:15:00')")

c.execute("INSERT INTO posts (id, title, content, created_at, view_count, author_id) VALUES (1, 'Hello World', 'My first post', '2024-01-16 11:00:00', 42, 1)")
c.execute("INSERT INTO posts (id, title, content, created_at, view_count, author_id) VALUES (2, 'Python Tips', 'Use list comprehensions', '2024-02-21 15:00:00', 100, 2)")
c.execute("INSERT INTO posts (id, title, content, created_at, view_count, author_id) VALUES (3, 'Flask Guide', 'Building REST APIs', '2024-03-11 10:00:00', 75, 1)")
c.execute("INSERT INTO posts (id, title, content, created_at, view_count, author_id) VALUES (4, 'SQL Basics', 'Understanding joins', '2024-03-15 08:00:00', 30, 3)")

conn.commit()
conn.close()
print("Created drifted database with sample data.")
PY

# Show the drift
echo "--- Current DB schema (drifted) ---"
python -c "
from sqlalchemy import create_engine, inspect
engine = create_engine('sqlite:///app.db')
inspector = inspect(engine)
for table in inspector.get_table_names():
    cols = [c['name'] for c in inspector.get_columns(table)]
    print(f'{table}: {cols}')
"

echo ""
echo "--- Validation (should fail) ---"
python validate_models.py || true

echo ""
echo "Setup complete. Database schema has drifted from models."
