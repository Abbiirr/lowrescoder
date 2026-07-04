#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/migrate.py << 'PYEOF'
"""Database migration script — NOT idempotent (crashes on second run)."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")


def run_migration():
    """Run database migration.

    BUG: This crashes on second run because:
    1. CREATE TABLE fails if table already exists
    2. INSERT adds duplicate seed data
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables (fails if they already exist)
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert seed data (duplicates on second run)
    cursor.execute("INSERT INTO users (username, email) VALUES ('admin', 'admin@example.com')")
    cursor.execute("INSERT INTO settings (key, value) VALUES ('version', '1.0')")
    cursor.execute("INSERT INTO settings (key, value) VALUES ('maintenance_mode', 'false')")
    cursor.execute("INSERT INTO settings (key, value) VALUES ('max_users', '1000')")

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    run_migration()
PYEOF

# Run migration once to create initial state
cd project
python3 migrate.py
cd ..

cat > project/test_migrate.py << 'PYEOF'
"""Tests for idempotent migration."""
import unittest
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")


def run_migration_safe():
    """Import and run migration, catching errors."""
    from migrate import run_migration
    run_migration()


class TestMigrationIdempotent(unittest.TestCase):

    def test_second_run_no_error(self):
        """Running migration again should not raise any exception."""
        try:
            run_migration_safe()
        except Exception as e:
            self.fail(f"Migration failed on second run: {e}")

    def test_third_run_no_error(self):
        """Running migration a third time should also work."""
        try:
            run_migration_safe()
            run_migration_safe()
        except Exception as e:
            self.fail(f"Migration failed on third run: {e}")

    def test_tables_exist(self):
        """All 3 tables should exist after migration."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        self.assertIn("users", tables)
        self.assertIn("settings", tables)
        self.assertIn("audit_log", tables)

    def test_no_duplicate_users(self):
        """Admin user should appear exactly once."""
        run_migration_safe()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1, f"Expected 1 admin user, got {count}")

    def test_no_duplicate_settings(self):
        """Settings should not be duplicated."""
        run_migration_safe()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM settings")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 3, f"Expected 3 settings, got {count}")

    def test_data_preserved(self):
        """Existing data should be preserved after re-running migration."""
        # Add custom data
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email) VALUES ('testuser', 'test@example.com')")
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Already exists from previous test run
        conn.close()

        # Run migration again
        run_migration_safe()

        # Check custom data is still there
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'testuser'")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, 1, "Custom data was lost after migration")

    def test_schema_correct(self):
        """Table columns should be correct."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        self.assertIn("id", columns)
        self.assertIn("username", columns)
        self.assertIn("email", columns)
        self.assertIn("created_at", columns)


if __name__ == "__main__":
    unittest.main()
PYEOF

echo "Setup complete. migrate.py crashes on second run — needs to be made idempotent."
