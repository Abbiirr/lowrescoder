"""Flask API with reports — missing CSV export feature."""
from flask import Flask, jsonify, request

app = Flask(__name__)

REPORTS = [
    {"id": 1, "title": "Q1 Sales", "amount": 15000.50, "date": "2025-03-31"},
    {"id": 2, "title": "Q2 Sales", "amount": 22000.75, "date": "2025-06-30"},
    {"id": 3, "title": "Q3 Sales", "amount": 18500.00, "date": "2025-09-30"},
    {"id": 4, "title": "Q4 Sales", "amount": 31000.25, "date": "2025-12-31"},
]


@app.route("/api/reports")
def list_reports():
    return jsonify({"reports": REPORTS})


# TODO: Add /api/reports/export?format=csv endpoint that returns reports as CSV
# The CSV should have columns: id, title, amount, date
# Content-Type should be text/csv


if __name__ == "__main__":
    app.run(debug=True)
