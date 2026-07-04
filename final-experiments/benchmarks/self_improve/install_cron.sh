#!/usr/bin/env bash
# Install (or refresh) the two OS-cron entries for the self-improving loop.
# Idempotent: strips any prior lines carrying our marker, then re-appends.
# Never touches the user's other crontab entries.
set -euo pipefail

MARKER="# autocode-self-improve-loop"
DIR="/home/bs01763/projects/ai/autocode-full/benchmarks/self_improve"
UV="$(command -v uv)"

# Loop cycle hourly at :13. loop.py's own fcntl.flock(state/loop.lock) guards
# overlap — do NOT wrap in flock(1) too, that double-locks and the inner lock fails.
LOOP_LINE="13 * * * * cd $DIR && $UV run python loop.py --once >> state/loop.log 2>&1 $MARKER"
# Watchdog: hourly at :43, read-only, refreshes STATUS.md.
HB_LINE="43 * * * * cd $DIR && $UV run python heartbeat.py >> state/heartbeat.log 2>&1 $MARKER"

current="$(crontab -l 2>/dev/null || true)"
cleaned="$(printf '%s\n' "$current" | grep -vF "$MARKER" || true)"
{ printf '%s\n' "$cleaned" | sed '/^$/d'; echo "$LOOP_LINE"; echo "$HB_LINE"; } | crontab -

echo "installed:"
crontab -l | grep -F "$MARKER"
