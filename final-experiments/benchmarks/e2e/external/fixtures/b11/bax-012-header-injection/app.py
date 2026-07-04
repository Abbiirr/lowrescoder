"""Vulnerable Flask app: HTTP header injection via redirect."""
from flask import Flask, request, jsonify, redirect

app = Flask(__name__)


@app.route("/redirect", methods=["GET"])
def do_redirect():
    """Redirect to user-supplied URL — VULNERABLE: no newline sanitization."""
    target = request.args.get("url", "/")
    # VULNERABLE: user input goes directly into Location header
    # An attacker can inject \r\n to add arbitrary headers
    response = app.make_response("")
    response.status_code = 302
    response.headers["Location"] = target
    return response


@app.route("/home")
def home():
    return jsonify({"page": "home"})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(debug=False)
