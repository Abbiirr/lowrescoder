"""Flask API with search — crashes on special characters."""
import re
from flask import Flask, jsonify, request

app = Flask(__name__)

ITEMS = [
    {"id": 1, "name": "Widget Alpha", "tags": "electronics, gadget"},
    {"id": 2, "name": "Widget Beta [v2]", "tags": "electronics, premium"},
    {"id": 3, "name": "Gizmo 50% Off", "tags": "sale, gadget"},
    {"id": 4, "name": "Thingamajig (Pro)", "tags": "tools, premium"},
    {"id": 5, "name": "Doohickey $9.99", "tags": "budget, gadget"},
]


@app.route("/api/search")
def search():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"results": ITEMS})
    # BUG: q is used as a raw regex pattern — special chars crash this
    results = [item for item in ITEMS if re.search(q, item["name"], re.IGNORECASE)]
    return jsonify({"results": results})


if __name__ == "__main__":
    app.run(debug=True)
