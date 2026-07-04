from fastapi import FastAPI, HTTPException

app = FastAPI()

# ── Users ──────────────────────────────────────────────────────────────────
_users: dict[int, dict] = {}
_next_user_id = 1


@app.post("/users", status_code=201)
def create_user(body: dict) -> dict:
    global _next_user_id
    if not body.get("username"):
        raise HTTPException(400, "username required")
    uid = _next_user_id
    _next_user_id += 1
    _users[uid] = {"id": uid, "username": body["username"], "email": body.get("email", "")}
    return _users[uid]


@app.get("/users/{user_id}")
def get_user(user_id: int) -> dict:
    if user_id not in _users:
        raise HTTPException(404, "user not found")
    return _users[user_id]


@app.get("/users")
def list_users() -> list[dict]:
    return list(_users.values())


# ── Posts ──────────────────────────────────────────────────────────────────
_posts: dict[int, dict] = {}
_next_post_id = 1


@app.post("/posts", status_code=201)
def create_post(body: dict) -> dict:
    global _next_post_id
    if not body.get("title"):
        raise HTTPException(400, "title required")
    pid = _next_post_id
    _next_post_id += 1
    _posts[pid] = {
        "id": pid,
        "title": body["title"],
        "body": body.get("body", ""),
        "author_id": body.get("author_id"),
    }
    return _posts[pid]


@app.get("/posts/{post_id}")
def get_post(post_id: int) -> dict:
    if post_id not in _posts:
        raise HTTPException(404, "post not found")
    return _posts[post_id]


@app.get("/posts")
def list_posts() -> list[dict]:
    return list(_posts.values())


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int) -> None:
    if post_id not in _posts:
        raise HTTPException(404, "post not found")
    del _posts[post_id]


# ── Comments ───────────────────────────────────────────────────────────────
_comments: dict[int, dict] = {}
_next_comment_id = 1


@app.post("/posts/{post_id}/comments", status_code=201)
def create_comment(post_id: int, body: dict) -> dict:
    global _next_comment_id
    if post_id not in _posts:
        raise HTTPException(404, "post not found")
    if not body.get("text"):
        raise HTTPException(400, "text required")
    cid = _next_comment_id
    _next_comment_id += 1
    _comments[cid] = {"id": cid, "post_id": post_id, "text": body["text"]}
    return _comments[cid]


@app.get("/posts/{post_id}/comments")
def list_comments(post_id: int) -> list[dict]:
    if post_id not in _posts:
        raise HTTPException(404, "post not found")
    return [c for c in _comments.values() if c["post_id"] == post_id]


def reset() -> None:
    global _next_user_id, _next_post_id, _next_comment_id
    _users.clear()
    _posts.clear()
    _comments.clear()
    _next_user_id = _next_post_id = _next_comment_id = 1
