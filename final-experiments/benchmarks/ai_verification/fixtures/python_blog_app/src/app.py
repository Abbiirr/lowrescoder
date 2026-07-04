from flask import Flask, render_template, jsonify, request, abort

app = Flask(__name__, template_folder="../templates")

_posts: list[dict] = [
    {"id": 1, "title": "Getting Started", "body": "Welcome to the blog.", "tags": ["intro", "welcome"], "published": True},
    {"id": 2, "title": "Flask Tips", "body": "Use blueprints for large apps.", "tags": ["flask", "python"], "published": True},
    {"id": 3, "title": "Draft Post", "body": "Work in progress.", "tags": ["draft"], "published": False},
    {"id": 4, "title": "Advanced Python", "body": "Decorators and generators.", "tags": ["python", "advanced"], "published": True},
    {"id": 5, "title": "Testing 101", "body": "Write tests early.", "tags": ["testing", "python"], "published": True},
]
_next_id = 6


def reset():
    global _next_id
    _posts.clear()
    _posts.extend([
        {"id": 1, "title": "Getting Started", "body": "Welcome to the blog.", "tags": ["intro", "welcome"], "published": True},
        {"id": 2, "title": "Flask Tips", "body": "Use blueprints for large apps.", "tags": ["flask", "python"], "published": True},
        {"id": 3, "title": "Draft Post", "body": "Work in progress.", "tags": ["draft"], "published": False},
        {"id": 4, "title": "Advanced Python", "body": "Decorators and generators.", "tags": ["python", "advanced"], "published": True},
        {"id": 5, "title": "Testing 101", "body": "Write tests early.", "tags": ["testing", "python"], "published": True},
    ])
    _next_id = 6


@app.get("/")
def index():
    published = [p for p in _posts if p["published"]]
    return render_template("index.html", posts=published)


@app.get("/posts/<int:post_id>")
def view_post(post_id: int):
    post = next((p for p in _posts if p["id"] == post_id), None)
    if post is None:
        abort(404)
    return render_template("post.html", post=post)


@app.get("/admin")
def admin():
    return render_template("admin.html", posts=_posts)


@app.get("/api/posts")
def api_posts():
    return jsonify([p for p in _posts if p["published"]])


@app.post("/api/posts")
def api_create_post():
    global _next_id
    data = request.get_json(force=True)
    if not data or not data.get("title"):
        abort(400)
    post = {
        "id": _next_id,
        "title": data["title"],
        "body": data.get("body", ""),
        "tags": data.get("tags", []),
        "published": data.get("published", False),
    }
    _next_id += 1
    _posts.append(post)
    return jsonify(post), 201
