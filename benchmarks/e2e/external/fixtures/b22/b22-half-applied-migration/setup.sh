#!/usr/bin/env bash
set -euo pipefail

# Create the full migration SQL file
cat > migration.sql << 'SQL'
-- Migration: 001_initial_schema
-- Creates the core application tables

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (author_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    post_id INTEGER NOT NULL,
    FOREIGN KEY (post_id) REFERENCES posts(id)
);

-- Record migration completion
INSERT INTO migration_log (migration_name, applied_at)
VALUES ('001_initial_schema', CURRENT_TIMESTAMP);
SQL

# Create the database with only partial tables applied (using Python's sqlite3)
python3 << 'PYSETUP'
import sqlite3

conn = sqlite3.connect("app.db")
c = conn.cursor()

# Migration log table (always created first)
c.execute("""
CREATE TABLE migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Only users and posts were created before the crash
c.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
c.execute("INSERT INTO users (username, email) VALUES ('admin', 'admin@example.com')")

c.execute("""
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users(id)
)
""")
c.execute("INSERT INTO posts (title, body, author_id) VALUES ('First Post', 'Hello world!', 1)")

conn.commit()
conn.close()
PYSETUP

echo "Setup complete. Database has users and posts tables but is missing comments and tags."
