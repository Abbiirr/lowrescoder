"""Raw sqlite3 database layer — to be migrated to SQLAlchemy."""

import sqlite3
from pathlib import Path

DB_PATH = Path("data.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )"""
        )


def create_user(name: str, email: str) -> dict:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)", (name, email)
        )
        return {"id": cur.lastrowid, "name": name, "email": email}


def get_user(user_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def list_users() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM users").fetchall()
        return [dict(r) for r in rows]
