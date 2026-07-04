"""Flask API with content management — missing role-based access control."""
from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory "database"
ARTICLES = [
    {"id": 1, "title": "First Post", "content": "Hello world", "author": "admin"},
    {"id": 2, "title": "Second Post", "content": "Another article", "author": "editor1"},
]

USERS = {
    "admin": {"role": "admin"},
    "editor1": {"role": "editor"},
    "viewer1": {"role": "viewer"},
}

# TODO: Add role-based access control
# - Role is passed via X-User header (simplified auth)
# - admin: can read, create, edit, delete
# - editor: can read, create, edit (own articles only)
# - viewer: can only read
# - Unauthorized actions should return 403


@app.route("/api/articles")
def list_articles():
    return jsonify({"articles": ARTICLES})


@app.route("/api/articles/<int:article_id>")
def get_article(article_id):
    article = next((a for a in ARTICLES if a["id"] == article_id), None)
    if article is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(article)


@app.route("/api/articles", methods=["POST"])
def create_article():
    data = request.get_json()
    user = request.headers.get("X-User", "anonymous")
    new_id = max(a["id"] for a in ARTICLES) + 1 if ARTICLES else 1
    article = {
        "id": new_id,
        "title": data.get("title", ""),
        "content": data.get("content", ""),
        "author": user,
    }
    ARTICLES.append(article)
    return jsonify(article), 201


@app.route("/api/articles/<int:article_id>", methods=["PUT"])
def update_article(article_id):
    article = next((a for a in ARTICLES if a["id"] == article_id), None)
    if article is None:
        return jsonify({"error": "not found"}), 404
    data = request.get_json()
    article["title"] = data.get("title", article["title"])
    article["content"] = data.get("content", article["content"])
    return jsonify(article)


@app.route("/api/articles/<int:article_id>", methods=["DELETE"])
def delete_article(article_id):
    global ARTICLES
    article = next((a for a in ARTICLES if a["id"] == article_id), None)
    if article is None:
        return jsonify({"error": "not found"}), 404
    ARTICLES = [a for a in ARTICLES if a["id"] != article_id]
    return jsonify({"deleted": article_id})


if __name__ == "__main__":
    app.run(debug=True)
