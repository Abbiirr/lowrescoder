from flask import Flask, render_template, jsonify

app = Flask(__name__, template_folder="../templates")

_items = [
    {"id": 1, "name": "Widget A", "price": 9.99},
    {"id": 2, "name": "Widget B", "price": 19.99},
]


@app.get("/")
def index():
    return render_template("index.html", items=_items)


@app.get("/api/items")
def api_items():
    return jsonify(_items)
