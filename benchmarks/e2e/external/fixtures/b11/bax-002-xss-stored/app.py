"""Vulnerable Flask app: Stored XSS via unescaped HTML output."""
from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory comment storage
comments = []


@app.route("/comments", methods=["GET"])
def get_comments():
    """Return all comments as raw HTML — VULNERABLE to stored XSS."""
    html_parts = ["<html><body><h1>Comments</h1>"]
    for comment in comments:
        # VULNERABLE: renders user input as raw HTML without escaping
        html_parts.append(f"<div class='comment'>{comment}</div>")
    html_parts.append("</body></html>")
    return "\n".join(html_parts), 200, {"Content-Type": "text/html"}


@app.route("/comments", methods=["POST"])
def add_comment():
    """Add a new comment."""
    data = request.get_json()
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "text required"}), 400
    comments.append(text)
    return jsonify({"status": "ok", "count": len(comments)}), 201


@app.route("/comments/clear", methods=["POST"])
def clear_comments():
    """Clear all comments (for testing)."""
    comments.clear()
    return jsonify({"status": "cleared"})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=False)
