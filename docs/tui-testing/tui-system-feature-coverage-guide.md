# TUI System Feature Coverage Guide

Guide for scenes that are not "just frontend chrome."

These states need real system behavior behind them:

- planning / todo lists
- task queues and subagents
- restore / checkpoints
- review / diff
- grep / search
- escalation / permissions

If you only capture idle overlays, you will miss the real product risk.

## Core Rule

A blocked system-feature scene does not become valid because we found a clever
way to fake a screenshot. It becomes valid when:

1. the product exposes a visible surface for the state
2. the state can be triggered deterministically
3. the capture proves real user-visible behavior

## Coverage Matrix

| Feature area | Why it is not frontend-only | Recommended trigger source | Capture timing | Visible assertions required | Current status |
|---|---|---|---|---|---|
| plan / todo | needs real task structure, current step, blocked/done state | benchmark run or scripted long-running task with planning enabled | mid-run and final | plan rows, active step, blocked/done states, not just `[PLAN]` in HUD | blocked |
| subagents / task queue / command center | depends on concurrent tasks, subagents, tool calls, queue depth | benchmark or richer mock fixture that emits tasks, subagents, and tool state | mid-run | task list, subagent rows, queue content, HUD counts | approximate only |
| restore / checkpoints | needs actual checkpoint inventory and restore workflow | checkpoint fixture plus restore action flow | mid-run and post-restore | restore selector, checkpoint metadata, success/failure result | blocked |
| review / diff | needs file/hunk metadata and user review actions | real review scenario or dedicated diff fixture | mid-run | file path, diff body, action hints, review state | blocked |
| grep / search | needs indexed results and selection workflow | search fixture or repo-backed search scenario | mid-run | query input, result list, selection marker, chosen result details | blocked |
| escalation / permissions | depends on protected-path policy and approval flow | protected-path fixture or sandboxed benchmark path | mid-run | reason text, approval options, pending/approved/denied states | blocked |

## What To Capture For Each Feature

### Plan / Todo

Required evidence:

- a frame where planning is visibly active
- a frame where at least one task is running or blocked
- a final frame showing whether the plan stayed visible or collapsed

What is not enough:

- only `[PLAN]` in the HUD
- only `Plan mode -> planning` in scrollback

### Subagents / Queue / Command Center

Required evidence:

- task panel open
- at least one task row
- at least one subagent row
- tool activity or queue content

Current nearest helper:

- `__PANELS__` from `autocode/tests/pty/mock_backend.py`

Current limitation:

- it is still an approximation, not a full command-center surface

### Restore / Checkpoints

Required evidence:

- a seeded checkpoint source
- a visible restore selection surface
- a follow-up frame proving restore success or failure

Current limitation:

- no live restore overlay exists yet

### Review / Diff

Required evidence:

- visible file identity
- visible diff or review content
- visible review actions

Current limitation:

- approval modal is not a substitute for review/diff focus

### Grep / Search

Required evidence:

- query entry
- visible results list
- selection marker
- visible selected result context

Current limitation:

- no first-class search UI exists yet

### Escalation / Permissions

Required evidence:

- reason for escalation
- visible decision options
- outcome after approve or deny

Current limitation:

- no deterministic escalation flow exists yet

## Benchmark-Driven Captures

Use benchmark or long-running flows when the interesting UI only appears while
the system is doing real work.

Recommended pattern:

1. start the scenario
2. open any required panel (`Ctrl+T`, palette, picker, restore flow)
3. capture frames while the work is still active
4. keep the benchmark command in the artifact alongside the screenshots

Current helper:

```bash
cd autocode
uv run python tests/tui-references/capture_frame_sequence.py \
  --name active-demo \
  --preset active
```

For scenes without presets yet, use explicit scripted steps and store the exact
command you ran in the QA artifact.

## Where These Results Belong

- Screens: `autocode/docs/qa/tui-frame-sequences/`
- Comparison bundles: `autocode/docs/qa/tui-reference-comparison/`
- Written analysis: `autocode/docs/qa/test-results/`

## Promotion Rule

Do not remove a Track 4 `xfail` for a system-feature scene until all three are
true:

1. the live state is real
2. the capture path is deterministic
3. the visible assertions are strong enough to catch regressions
