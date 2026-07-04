# Anvil — copycat mode (PLAN_05, Channel A)

Anvil is AutoCode's **offline** harness-evolution engine. This directory holds
copycat mode's data; the code lives in `src/autocode/anvil/`.

**Copycat mode** acquires capability through *Channel A — structural imitation*:
read the public, observable structure of a strong harness (here, **puku-cli**),
diff it against AutoCode's own capability manifest, and draft *clean-room*
capability proposals. It never vendors third-party source — proposals become new
AutoCode components evaluated on AutoCode's own oracle.

## The manual MVP loop

```sh
autocode anvil copycat registry                      # list authorized targets
autocode anvil copycat census   puku-cli             # write copycat/census/puku-cli.yaml
autocode anvil copycat gap-diff puku-cli             # diff vs AutoCode's manifest
autocode anvil copycat gap-diff puku-cli --json      # machine-readable gap report
autocode anvil copycat propose  puku-cli flag:permission-mode   # draft patch_bundles/pb_NNN/
autocode anvil gate    pb_001                         # run the bundle's check plan (the oracle)
autocode anvil promote pb_001                         # record the promotion in audit_log.jsonl
```

Every step is **registry-gated** (`copycat/registry.yaml` is the hard gate, and
is intentionally outside Anvil's action space). The operator is the gate at every
step — manual-first by design.

## Layout

| Path | Role |
|---|---|
| `copycat/registry.yaml` | **tracked input** — authorized targets + `reuse_scope` |
| `copycat/census/<target>.yaml` | generated — a target's observable capability set |
| `patch_bundles/pb_NNN/` | generated — `decision.md`, `prediction_contract.yaml`, `manifest_delta.yaml`, `eval_report.json`, `prediction_score.json`, `bundle.json` |
| `audit_log.jsonl` | generated — the immutable promotion log |

Generated paths are git-ignored; the registry is the tracked input.

## Features already copied from puku-cli (clean-room)

All five are additive — omitting the flag preserves prior `exec` behavior exactly.

| puku-cli surface | AutoCode capability (landed) |
|---|---|
| `--permission-mode <mode>` | `autocode exec --permission-mode acceptEdits\|bypassPermissions\|default\|dontAsk\|plan\|auto` — maps onto AutoCode's existing `ApprovalMode` (`src/autocode/agent/permission_mode.py`). |
| `--max-budget-usd <amount>` | `autocode exec --max-budget-usd <amount>` — a per-run override of AutoCode's existing `agent.cost_limit_usd` engine. |
| `--system-prompt <text>` | `autocode exec --system-prompt <text>` — replaces the persona region, preserves dynamic runtime state (`finalize_system_prompt` in `agent/prompts.py`). |
| `--append-system-prompt <text>` | `autocode exec --append-system-prompt <text>` — appends to the assembled system prompt. |
| `--add-dir <dir>` | `autocode exec --add-dir <dir>` (repeatable) — opt-in `extra_roots` allow-list extending `validate_path` confinement; empty default = unchanged sandbox. |

As of the latest gap-diff there are **0 clean-room-suitable gaps remaining** — every
curated-suitable puku-cli capability has been copied. The remaining gaps
(`--model`, `--provider`, `--effort`, `--agents`, MCP config, worktrees, …) are
classified non-suitable: each needs deliberate design work (model/provider
routing, session-persistence model, MCP loading), not a clean additive port.

`tests/unit/test_anvil_live_puku.py` guards these against drift: it runs the real
`puku-cli` binary and asserts the parser still recovers the surface and that all
five copied features stay present in AutoCode's manifest.

## Teacher mode (PLAN_04) coexists here

Anvil's teacher leg mounts under the same app as `autocode anvil teacher ...`.
Copycat (PLAN_05) and teacher (PLAN_04) share the `anvil` command group but are
independent; copycat's capability proposals are designed to feed the teacher's
`harness_fix` candidates.
