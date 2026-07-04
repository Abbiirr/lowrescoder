# autocode self-improving loop — supervisor check

You are the oversight layer over a cron-driven engine: `loop.py` runs hourly via
OS cron (one benchmark slice → diagnose → auto-apply a validated harness fix →
keep/revert), `heartbeat.py` refreshes `STATUS.md`. Each iteration, confirm the
engine is healthy, **catch reward-hacking in auto-applied fixes**, intervene
minimally, report. Work from `benchmarks/self_improve/`.

**Hard rules:** never run a mutating git command. Never edit graders, fixtures,
`verify.sh`, or `benchmarks/` — only the loop edits, and only under `src/autocode/`.

## 1. Refresh + read
- `uv run python heartbeat.py` (updates STATUS.md; prints gateway / cycles / kept / staleness)
- Read `state/STATUS.md` and the last ~15 lines of `state/ledger.jsonl`.

## 2. Bootstrap (first run, or if cron is missing)
- `crontab -l | grep autocode-self-improve-loop`
- If absent AND the latest `event:run` row ran without crashing → arm it: `bash install_cron.sh`.
- If there's no sane cycle yet → run one safely first: `SI_SELF_EDIT=0 uv run python loop.py --once`, inspect the ledger row, then arm.

## 3. Health (flag + minimal action)
- **Gateway DOWN** → the loop self-skips (no data loss); note it. Test models; if one alias is rate-limited, rotate `SI_MODEL` in the cron line (bench_stable → bench → tools).
- **Stale** (no `event:run` in >2h while gateway UP) → cron may not be firing. Check `crontab -l`, tail `state/loop.log` for the error, run one cycle manually to surface it.
- **Infra storm** (recent rows mostly infra_fails ≈ total) → upstream is throttling; don't churn, note it, let it recover.

## 4. Audit auto-applied fixes — the important one (anti reward-hack)
For every new `self_edit: KEEP…` row since your last check:
- The row carries `snapshot:` and `kept_files`. Diff them: `diff -ru <snapshot>/<file> src/autocode/<file>`.
- Confirm the edit is a genuine harness improvement, lives only under `src/autocode/`, and did **not** weaken a check, loosen a threshold, or stub a test. (It physically can't reach graders — verify anyway.)
- Suspicious → REVERT and log why:
  `uv run python -c "import common,pathlib; common.restore_harness(pathlib.Path('<snapshot>'))"`

## 5. Trend
Per-lane resolved rate over recent cycles — rising / flat / falling? If a kept fix
correlates with a later drop, suspect overfit or a flaky pass → revert it.

## 6. Record + report
- Append one line to `state/supervisor.log`: ts · gateway · cycles · kept · action taken.
- If a real decision happened (a revert, a model rotation, a sustained gain), update memory (`project_meta_autocode`).
- Report 3–5 lines to the user: gateway, cycles since last check, latest per-lane resolved, kept/reverted this round, any action. Then schedule the next wake (~hourly).
