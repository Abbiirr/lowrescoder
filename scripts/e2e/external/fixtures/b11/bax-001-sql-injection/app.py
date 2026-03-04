"""Vulnerable Flask app: SQL Injection via string formatting."""
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = ":memory:"


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        "CREATE TABLE IF NOT EXISTS users "
        "(id INTEGER PRIMARY KEY, username TEXT, password TEXT)"
    )
    db.execute(
        "INSERT OR IGNORE INTO users (id, username, password) "
        "VALUES (1, 'admin', 'supersecret')"
    )
    db.commit()
    return db


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    db = get_db()
    # VULNERABLE: string formatting in SQL query
    query = (
        "SELECT * FROM users WHERE username = '%s' AND password = '%s'"
        % (username, password)
    )
    cursor = db.execute(query)
    user = cursor.fetchone()
    if user:
        return jsonify({"status": "ok", "user": user[1]}), 200
    return jsonify({"status": "denied"}), 401


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=False)
