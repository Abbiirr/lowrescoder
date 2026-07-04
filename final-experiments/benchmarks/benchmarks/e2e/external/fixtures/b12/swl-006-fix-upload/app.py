"""Flask API with file upload — large file error not handled."""
from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB

UPLOADS = []


@app.route("/api/upload", methods=["POST"])
def upload_file():
    # BUG: when a file exceeds MAX_CONTENT_LENGTH Flask raises
    # RequestEntityTooLarge (413) but this handler doesn't catch it,
    # so the client gets an ugly HTML error page instead of JSON.
    f = request.files.get("file")
    if f is None:
        return jsonify({"error": "no file provided"}), 400
    entry = {"filename": f.filename, "size": len(f.read())}
    UPLOADS.append(entry)
    return jsonify(entry), 201


@app.route("/api/uploads")
def list_uploads():
    return jsonify({"uploads": UPLOADS})


if __name__ == "__main__":
    app.run(debug=True)
