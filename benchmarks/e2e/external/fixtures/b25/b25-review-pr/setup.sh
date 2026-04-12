#!/usr/bin/env bash
set -euo pipefail

mkdir -p project

cat > project/pr_diff.patch << 'EOF'
diff --git a/app/auth.py b/app/auth.py
index 1234567..abcdef0 100644
--- a/app/auth.py
+++ b/app/auth.py
@@ -1,6 +1,8 @@
 import hashlib
+import sqlite3
 from flask import request, jsonify

+DB_PATH = "/var/app/users.db"

 def login(username, password):
     """Authenticate a user and return a token."""
@@ -8,10 +10,15 @@ def login(username, password):
     if not username or not password:
         return jsonify({"error": "Missing credentials"}), 400

-    user = User.query.filter_by(username=username).first()
-    if user and user.check_password(password):
-        token = generate_token(user)
-        return jsonify({"token": token}), 200
+    # ISSUE 1 (Security): SQL injection vulnerability
+    conn = sqlite3.connect(DB_PATH)
+    cursor = conn.cursor()
+    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
+    cursor.execute(query)
+    user = cursor.fetchone()
+    if user:
+        token = hashlib.md5(username.encode()).hexdigest()  # ISSUE 2 (Security): MD5 for tokens
+        return jsonify({"token": token}), 200

     return jsonify({"error": "Invalid credentials"}), 401

@@ -20,8 +27,14 @@ def get_users():
     """Return all users for the admin dashboard."""
-    users = User.query.all()
-    return jsonify([u.to_dict() for u in users])
+    # ISSUE 3 (Performance): Loading ALL users without pagination
+    conn = sqlite3.connect(DB_PATH)
+    cursor = conn.cursor()
+    cursor.execute("SELECT * FROM users")
+    users = cursor.fetchall()  # Could be millions of rows
+    result = []
+    for user in users:
+        result.append({"id": user[0], "name": user[1], "email": user[2], "password": user[3]})  # ISSUE 4 (Security): Exposing password field
+    return jsonify(result)


 def update_profile(user_id):
@@ -30,6 +43,10 @@ def update_profile(user_id):
     data = request.get_json()
-    user = User.query.get(user_id)
-    user.name = data.get("name", user.name)
-    user.save()
+    conn = sqlite3.connect(DB_PATH)
+    cursor = conn.cursor()
+    # ISSUE 5 (Style): No input validation, no error handling
+    cursor.execute(f"UPDATE users SET name = '{data['name']}' WHERE id = {user_id}")
+    conn.commit()
+    conn.close()
     return jsonify({"status": "updated"}), 200
EOF

cat > project/review_template.md << 'EOF'
# Pull Request Review

## Summary
<!-- Brief description of what the PR does -->

## Issues Found

### Issue 1
- **Category:** (security / performance / style / bug)
- **Severity:** (critical / high / medium / low)
- **Location:** (file and line reference)
- **Description:**
- **Suggested fix:**

### Issue 2
- **Category:**
- **Severity:**
- **Location:**
- **Description:**
- **Suggested fix:**

### Issue 3
- **Category:**
- **Severity:**
- **Location:**
- **Description:**
- **Suggested fix:**

<!-- Add more issues as needed -->

## Verdict
**Decision:** (APPROVE / REQUEST CHANGES)
**Rationale:**

## Positive Aspects
<!-- Anything good about the PR worth noting -->
EOF

echo "Setup complete. PR diff contains security, performance, and style issues."
