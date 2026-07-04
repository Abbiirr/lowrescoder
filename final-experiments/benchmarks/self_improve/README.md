# autocode self-improving benchmark loop

Cron-driven. No daemon. Each tick runs **one** benchmark slice, diagnoses
failures, and (auto-apply mode) lets `autocode` patch its own harness — kept
only if a failing task starts passing with zero regression.

## Files
- `loop.py --once` — one cycle (run → diagnose → propose → validate → keep/revert). flock-guarded.
- `heartbeat.py` — read-only watchdog; refreshes `state/STATUS.md`, exits non-zero if unhealthy.
- `common.py` — paths, gateway env, ledger, snapshot/revert, status render.
- `state/` — `ledger.jsonl` (every cycle), `STATUS.md` (human view), `backups/<ts>/` (harness snapshots for rollback), `cursor.json` (lane round-robin), `tb_ready` (touch to enable B30-TBENCH).

## Safety rails (auto-apply mode)
1. Harness is snapshotted before every self-edit → `restore_harness()` reverts (no git needed).
2. The propose step runs `autocode exec --cd autocode/`, so the agent is rooted in the harness package and **cannot reach** `benchmarks/` or the graders. It cannot disable its own checker.
3. An edit is kept only if a real FAIL becomes RESOLVED **and** no previously-passing task regresses. Syntax-broken or no-gain edits auto-revert.

## Run by hand
```bash
cd benchmarks/self_improve
SI_SELF_EDIT=0 uv run python loop.py --once   # safe: run+diagnose only, no edits
uv run python loop.py --once                  # full cycle (auto-apply on)
uv run python heartbeat.py                     # status now
cat state/STATUS.md
```

## Knobs (env)
`SI_LANES`, `SI_MODEL` (default bench_stable), `SI_PROPOSE_MODEL` (coding),
`SI_MAX_TASKS` (4), `SI_SELF_EDIT` (1), `SI_PROPOSE_BUDGET_USD` (0.50).

## Rollback a bad auto-applied fix
`ledger.jsonl` rows with `self_edit: KEEP...` carry `snapshot:` — restore it:
```python
import common; common.restore_harness(Path("state/backups/<ts>"))
```

## ponytail ceilings (upgrade path)
- No multi-seed noise floor yet — a flaky pass can look like a gain. Guard
  (no regression of passers) bounds the damage; add 3-seed validation if it bites.
- Snapshot covers `src/autocode/` only; an edit outside it (improbable, agent is
  rooted in autocode/) isn't auto-reverted.
- Lane round-robin is hardcoded; reorder via `SI_LANES`.
