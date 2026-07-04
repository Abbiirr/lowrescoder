#!/usr/bin/env bash
# Setup for b15-fix-slow-query
# Creates a Python app with a classic N+1 query problem.
set -euo pipefail

# Database setup and seeding
cat > db.py << 'PYTHON'
"""Database setup and seeding."""
import sqlite3
import os


DB_PATH = "app.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def setup_database():
    """Create tables and seed data."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            department_id INTEGER,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        )
    """)

    departments = [
        (1, "Engineering"),
        (2, "Marketing"),
        (3, "Sales"),
        (4, "Support"),
        (5, "HR"),
    ]
    cursor.executemany("INSERT INTO departments VALUES (?, ?)", departments)

    users = []
    for i in range(1, 101):
        dept_id = (i % 5) + 1
        users.append((i, f"User_{i}", f"user{i}@example.com", dept_id))
    cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?)", users)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    setup_database()
    print(f"Database seeded with 5 departments and 100 users.")
PYTHON

# Main application with N+1 query problem
cat > app.py << 'PYTHON'
"""Application with user listing functionality."""
import sqlite3
from db import get_connection


def get_user_list():
    """Get all users with their department names.

    Returns a list of dicts with keys: id, name, email, department_name
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get all users
    cursor.execute("SELECT id, name, email, department_id FROM users")
    users = cursor.fetchall()

    result = []
    for user in users:
        user_id, name, email, dept_id = user
        # Fetch department name for each user (N+1 problem!)
        dept_cursor = conn.cursor()
        dept_cursor.execute(
            "SELECT name FROM departments WHERE id = ?", (dept_id,)
        )
        dept_row = dept_cursor.fetchone()
        dept_name = dept_row[0] if dept_row else "Unknown"

        result.append({
            "id": user_id,
            "name": name,
            "email": email,
            "department_name": dept_name,
        })

    conn.close()
    return result


def get_user_count():
    """Get total number of users."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count


if __name__ == "__main__":
    users = get_user_list()
    print(f"Found {len(users)} users")
    for u in users[:5]:
        print(f"  {u['name']} ({u['email']}) - {u['department_name']}")
PYTHON

# Tests
cat > test_app.py << 'PYTHON'
"""Tests for user listing functionality."""
import os
import pytest
from db import setup_database
from app import get_user_list, get_user_count


@pytest.fixture(autouse=True)
def fresh_db():
    setup_database()
    yield
    if os.path.exists("app.db"):
        os.remove("app.db")


def test_user_list_returns_all_users():
    users = get_user_list()
    assert len(users) == 100


def test_user_list_has_correct_keys():
    users = get_user_list()
    for user in users:
        assert "id" in user
        assert "name" in user
        assert "email" in user
        assert "department_name" in user


def test_user_list_department_names():
    users = get_user_list()
    dept_names = {u["department_name"] for u in users}
    expected = {"Engineering", "Marketing", "Sales", "Support", "HR"}
    assert dept_names == expected


def test_user_list_data_correctness():
    users = get_user_list()
    user_1 = next(u for u in users if u["id"] == 1)
    assert user_1["name"] == "User_1"
    assert user_1["email"] == "user1@example.com"
    assert user_1["department_name"] in {
        "Engineering", "Marketing", "Sales", "Support", "HR"
    }


def test_user_count():
    assert get_user_count() == 100
PYTHON

# Set up the database
python db.py

echo "Setup complete. App with N+1 query problem created."
