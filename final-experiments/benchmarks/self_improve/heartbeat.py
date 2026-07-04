#!/usr/bin/env python
"""Read-only watchdog. Refreshes STATUS.md, prints a one-line summary, and exits
non-zero if the loop looks unhealthy so cron surfaces it. Never edits anything.
"""
from __future__ import annotations

from datetime import datetime, timezone

import common as c


def main() -> int:
    rows = c.read_ledger()
    healthy = c.gateway_healthy()
    c.render_status()

    runs = [r for r in rows if r.get("event") == "run"]
    keeps = sum(1 for r in runs if str(r.get("self_edit", "")).startswith("KEEP"))

    stale_min = None
    if rows:
        last = datetime.fromisoformat(rows[-1]["ts"])
        stale_min = (datetime.now(timezone.utc) - last).total_seconds() / 60

    staleness = f"{stale_min:.0f}m ago" if stale_min is not None else "never"
    print(
        f"[heartbeat] gateway={'UP' if healthy else 'DOWN'} "
        f"cycles={len(runs)} kept={keeps} last={staleness}"
    )

    # Unhealthy = gateway down, or no cycle in >3h (cron should fire hourly).
    if not healthy:
        return 2
    if stale_min is not None and stale_min > 180:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
