# Incident detection for heartbeat streams — has a bug.
# This file exists to be fixed by the agent.


def detect_incidents(heartbeats: list[dict]) -> list[dict]:
    """Detect down-incidents from a heartbeat list.

    Each heartbeat has {'status': 'up'|'down', 'ts': int}.
    Returns a list of incidents: {'start': ts, 'end': ts|None}
    where end=None means the incident is still ongoing.

    Bug: the final incident is lost when heartbeats ends while still 'down',
    because the closing append only runs on the 'up' transition — never at EOF.
    """
    incidents = []
    in_incident = False
    start_ts = None

    for hb in heartbeats:
        if hb["status"] == "down" and not in_incident:
            in_incident = True
            start_ts = hb["ts"]
        elif hb["status"] == "up" and in_incident:
            in_incident = False
            incidents.append({"start": start_ts, "end": hb["ts"]})

    # BUG: if stream ends while in_incident, we never append the open incident
    return incidents
