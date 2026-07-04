"""Flask API for event scheduling — timezone handling is broken."""
from datetime import datetime

from flask import Flask, jsonify, request

app = Flask(__name__)

EVENTS = []


@app.route("/api/events", methods=["GET"])
def list_events():
    return jsonify({"events": EVENTS})


@app.route("/api/events", methods=["POST"])
def create_event():
    data = request.get_json()
    # Compute next ID from existing events (resets correctly when EVENTS cleared)
    next_id = max((e["id"] for e in EVENTS), default=0) + 1
    # BUG: ignores timezone info, stores raw string then re-parses without tz
    event = {
        "id": next_id,
        "title": data["title"],
        "start_time": data["start_time"],  # stored as raw string
    }
    EVENTS.append(event)
    return jsonify(event), 201


@app.route("/api/events/<int:event_id>/display_time")
def display_time(event_id):
    tz_name = request.args.get("tz", "UTC")
    event = next((e for e in EVENTS if e["id"] == event_id), None)
    if event is None:
        return jsonify({"error": "not found"}), 404

    # BUG: parses without timezone awareness, ignores the tz param
    dt = datetime.fromisoformat(event["start_time"].replace("Z", ""))
    return jsonify({
        "id": event["id"],
        "title": event["title"],
        "display_time": dt.isoformat(),
        "timezone": tz_name,
    })


if __name__ == "__main__":
    app.run(debug=True)
