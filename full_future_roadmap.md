# Full Roadmap - As Far As I Can See (2026-05-02)

> Status: strategic projection only. Active execution authority is `next_remaining_plan.md`, `next_remaining_todo.md`, and the current HFIX plan at `docs/plan/ai-verification-harness-fixes-plan.md`.
> Refresh trigger: update this file only when the active plan changes enough to affect horizons or sequencing.

Visibility honesty: high confidence for the next 1-3 months (current pass + immediate follow-up tranche, all already scoped); medium confidence for 3-6 months (deferred items have shapes but specific sequencing depends on signals); sketches for 6-12 months (capability tracks I can extrapolate but not yet planned); speculation beyond that.

---

## Horizon 0 - Active Pass (0-1 Week, In Flight; HFIX Priority)

Single commit at the end of this horizon per User Option C lock-in (Entry 1743).
User direction on 2026-05-02 promotes AI verification harness fixes before P3b resumes.

| Phase | State | Adds | Test surface (proj.) |
|---|---|---|---|
| P0 -> P3 | closed | substrate + telemetry + cache + scratch + memory | 2217 unit / 29 substrate |
| HR foundation + migration | closed (Entries 1734, 1737) | Hook Protocol + Dispatcher + 4 extracted hooks | 2230 unit |
| P3a Drift detectors | closed (Entry 1743) | SchemaDrift + ContextStaleness + ToolConsistency + Hook + telemetry + CLI | 2244 unit |
| HFIX AI verification harness fixes | active priority | Structured tool/turn events + per-turn/run summaries + required-tool/non-empty-diff guards + spawn/ask-user/semantic canaries + harness self-validation | substrate + fresh multi-turn runs |
| P3b PEV + Ralph | paused until HFIX closes | Plan-Execute-Verify scaffolding + Ralph recovery driver + IntentStore | ~2280-2310 |
| P3c Entropy + verify tightening | queued | Entropy auditor + verify-before-use hardening | ~2310-2340 |
| P3d Eval suite expansion | queued; consumes HFIX outputs | Eval runner + judge + CI gate (soft->hard) + drift->eval generator + regression discipline | ~2380-2420 |
| P5 KAIROS | queued, default OFF | ProactiveLoop + TickConfig + SleepTool + 15s blocking budget + anti-narration prompt + `autocode daemon --watch` | ~2420-2450 |
| Final batch APPROVE | Claude verdict | - | - |
| User commits stable codebase | - | - | - |

Total new tests this horizon: ~+220 over current 2244. LOC delta: ~+1650 net.

Critical-path risk: P3d's eval-judge needs a stronger model than the agent (per `next_remaining_todo.md:692`); gateway alias availability matters. Mitigation: judge already gateway-aliased; no provider lock-in.

### Horizon 0 Scope Boundary - Harness Backend Testing Only

The `harness-tester/` package added during HFIX is scoped to harness backend testing, not TUI testing.

Current in-scope surfaces:

- AI verification harness backend execution.
- Headless agent runner and session continuity.
- Scripted multi-turn scenario orchestration.
- Scenario grading and verdict composition.
- Structured tool-call trace artifacts.
- Turn/session ledgers and backend artifact preservation.
- Future semi-automated prompter control via manual or file-mediated agent prompt decisions.

Out of scope for the current `harness-tester/` pass and deferred to the future TUI path:

- Rust TUI rendering.
- TUI visual regression.
- PTY smoke for interactive UI behavior.
- VHS snapshot capture and comparison.
- Track 1 TUI runtime-invariant testing.
- Track 4 TUI design-target ratchet testing.

These TUI items remain under Horizon 1A (`TUI Path A Refactor Pass`) and should not be used as HFIX exit criteria.

---

## Horizon 1 - Immediate Follow-Up Tranche (4-8 Weeks After Stable Commit)

Three parallel threads, each batched into its own pass per the established pattern (one stable commit per pass). All scope already captured in deferral tags.

### 1A - TUI Path A Refactor Pass (P4a-DEFERRED)

| Slice | Scope | LOC delta | Risk |
|---|---|---:|---|
| `rtui/src/render/view.rs` widget-per-mode | replace 9x9 stage x detail-surface match arms; render fns 30-60 LOC; layout depth <=2 | ~-2000 | medium - widget cache invalidation correctness |
| `HistoryEntry::cached_lines` | `RefCell<Option<(u16, Vec<Line<'static>>)>>` cached per entry; invalidate on mutation/width | ~-400 | low - well-understood pattern |
| `rtui/src/state/reducer.rs` Event collapse | 40+ Event variants -> `RpcMsg(Value)` + sub-reducer | ~-500 | medium - loss of compile-time exhaustiveness |
| Performance ratchet | cold-start <150ms; frame <5ms; binary <1.8MB; idle RSS <60MB | - | medium - measurement noise |
| Track 1/4/VHS/PTY all green | full TUI testing matrix | - | high - VHS PNG drift requires user gating |

Final TUI LOC: ~4600 (from 7500). Pass length: ~1.5 weeks. Trigger: User signals "ok pick up TUI now."

### 1B - Hook-Context Extension Pass (HR-EXT-{1,2,3})

| Item | What it unlocks | LOC delta |
|---|---|---:|
| HR-EXT-1 Prompt-cache hook context | Allow prompt-cache keepalive + cache-write telemetry through dispatcher | ~+150 |
| HR-EXT-2 LLM/tool telemetry hook context | Allow `llm_call_completed` + `tool_call_completed` via dispatcher with full payload | ~+200 |
| HR-EXT-3 Memory load hook context | Move factory/bootstrap memory load into a BootHook variant | ~+100 |
| Hook signature evolution | Extend Hook Protocol with per-event payload dataclasses; backwards-compat shim | ~+250 |

Pass length: ~1 week. Trigger: runs in parallel with (or right after) TUI pass. Why care: completes the HR vision - single source of truth for cross-cutting behavior; no more "two layers" criticism.

### 1C - Post-HFIX Harness Follow-Through

Most HARNESS-EXT-{4,5,6} scope was promoted into HFIX on 2026-05-02. This follow-up pass now covers only leftovers that remain after HFIX and P3d.

| Item | Value | LOC delta |
|---|---|---:|
| Legacy scenario migration to typed assertions | Converts older scenarios to the HFIX trace/assertion contract | ~+100-250 |
| Broader real-agent sweeps | Expands beyond the initial spawn/ask-user canaries once the contract is stable | variable |
| Eval-suite v3 integration polish | Feeds HFIX artifacts into multi-judge and failure-taxonomy work if P3d leaves gaps | ~+100 |

Pass length: ~0.5-1 week if needed. Trigger: HFIX/P3d closeout identifies remaining harness migration or coverage work.

Horizon 1 total: ~3-4 weeks of work, can run as 3 sequential small passes or 1 big mixed-tranche pass per User preference. Recommendation: 3 sequential - small surgical commits are easier to bisect.

---

## Horizon 2 - Mid-Term (3-6 Months)

Heavily dependent on telemetry baseline accumulating. Each item has an explicit unblock condition.

### 2A - KAIROS Promotion (Tier 4.1 v2)

| Stage | Condition | What ships |
|---|---|---|
| KAIROS v1 (P5, this pass) | - | Default OFF behind `AUTOCODE_FEATURE_KAIROS=true` |
| KAIROS v2 opt-in default | >=4 weeks of P1a telemetry baseline + observability story per `docs/plan/roadmaps/2026-04-30-tier-roadmap/04-tier4-future-tracks.md` | Default ON for opt-in users with `--dry-run` for first 2 weeks |
| KAIROS v3 trusted-env default | KAIROS v2 ran 4+ weeks with `kairos_action_blast_radius` p95 within budget + zero `requires_approval=True` violations | Default ON for first-party setups |

Risk: KAIROS is the highest blast-radius capability in the roadmap. Promotion gates are hard requirements, not nice-to-haves.

### 2B - Eval Suite v3

Builds on HFIX/P3d artifacts and any Horizon 1C follow-through.

- Multi-model judge ensemble (currently single judge); reduce judge variance.
- Eval case library expansion via drift->eval automation (initial >=1/30days threshold from P3d ramps to >=10/30days as production sessions accumulate).
- Qualitative criterion library: shared `criterion: code_quality`, `criterion: test_quality`, `criterion: minimality`, `criterion: cost_efficiency` definitions reused across cases.
- Eval case versioning + migration tooling (the append-only rule from P3d Rule 4 + automated migration when schema evolves).

### 2C - Telemetry v3

- Drift->eval automation flywheel matures: weekly cron generates eval candidates from production drift events.
- Failure-class taxonomy: structured FAIL categorization (tool error vs intent miss vs verify regression vs cost cap vs time cap vs drift-detected vs unknown).
- Production dashboards: optional Grafana export from `autocode telemetry export --format prometheus`.

### 2D - Reliability v2

- PEV/Ralph threshold calibration based on production telemetry (recovery loop count, recovery success rate, time-to-recover distribution).
- Drift detector sensitivity calibration (false-positive rate from P3a `agent.drift.schema.sensitivity` setting).
- Entropy auditor budget calibration (when does it trigger? what's the baseline entropy distribution per tool?).

---

## Horizon 3 - Long-Term (6-12 Months)

### 3A - Conditional Tier 2 Unlock

Hold-release triggers (from `next_remaining_plan.md:314`):

1. Concrete second client surface materializes (Tauri/Electron/web/IDE plugin/programmatic 3rd-party consumer).
2. `rtui/src/rpc/protocol.rs` exceeds 60 ad-hoc structs (currently 44).
3. Two concurrent backend consumers exist.

If any one fires -> propose Concern entry -> user decides whether to start P4 (Tier 2 Item/Turn/Thread) -> unlocks Tier 4.2 ephemeral fork + Tier 4.3 sticky env.

If unlocked, Tier 2 carries: typed primitives (Item/Turn/Thread/Stream); transports (Unix socket, WebSocket, stdio); turn/steer mid-flight input; canonical RPC schema versioning.

If Tier 2 stays locked: that's fine. Current monolith works for the single-TUI use case.

### 3B - Memory v3

- MemoryFS scaling: when `MEMORY.md` approaches 200 entries (currently 32), consider topic-file consolidation, daily-log rotation policy, or vector retrieval (deliberately omitted per north-star but reconsiderable on data).
- Cross-project memory awareness (with explicit user opt-in): allow `MEMORY.md` insights from project A to inform behavior in project B when explicitly linked.
- Pattern extraction from successful sessions: identify recurring (problem, approach, outcome) tuples and surface them as "have seen this before" hints.

### 3C - Cost / Budget Controls

Currently only `--max-budget-usd 5.00` cost cap on CI eval gate.

- Per-session budget caps with hard stop.
- Cost forecasting before tool calls (estimate before, reconcile after).
- Cost-routing per task class: planning tasks get bigger model, executing tasks get cheaper model, judging tasks get strongest model.
- Daily/weekly budget rollups via `autocode telemetry cost --last 7d`.

### 3D - Multi-Model Handoff

Today: single model per session. Future:

- Planner = strongest model (Opus 4.7+); generates `<plan>` block.
- Executor = cheapest competent model (Haiku 4.5); executes single tool calls.
- Judge = different strong model (Sonnet 4.6); independent verification.
- Recovery = stronger model when Ralph fires (escalation path).

This is a substantial architectural change - would need its own pass with thorough eval coverage to prove no quality regression.

### 3E - Replay / Determinism v2

- Record agent transcript with full tool I/O + LLM call payloads.
- Deterministically replay against same fixture: `autocode replay --transcript <id> --fixture <commit-sha>` produces identical diff.
- Time-travel debugging: `autocode replay --pause-at turn=3` for inspection.
- Diff-able execution traces for regression diagnosis.

---

## Horizon 4 - Strategic Horizon (12+ Months, Sketches)

These I can outline but not estimate with confidence.

### 4A - Sandbox v2 (Containerized Tool Execution)

If blast-radius incidents accumulate, the case for sandboxed execution gets stronger.

- Network isolation per turn (deny-by-default with explicit allowlist).
- Filesystem quota enforcement (deny tool calls that would exceed budget).
- Resource limits per tool call (CPU/memory/wall time).
- Containerized tool execution (Docker, podman, or namespace-based).

### 4B - Knowledge Persistence v2

If memory v3 scales, the next move is a personal-fine-tuned-model loop:

- Identify high-value sessions (PASS verdict + low cost + high `test_quality_score`).
- Aggregate (input, output) pairs into a personal training corpus.
- User-controlled fine-tuning of a personal model.
- Tradeoff: privacy vs. quality. Strict opt-in.

### 4C - Distribution / Packaging

Currently uv + cargo. As the user base grows:

- Single-binary distribution (PyInstaller / uv build / cargo install of a wrapper).
- Homebrew tap.
- Docker image.
- Auto-update channel with rollback support.

### 4D - Security / Compliance Mode

If used in regulated environments:

- Audit log signing (HMAC + tamper detection).
- PII detection in transcripts (regex + LLM scrubber).
- Compliance mode (read-only sessions; no tool calls outside an approved list).
- Centralized audit trail export.

### 4E - Conditional Reconsideration of "Deliberately Omitted" Items

The north-star list is not eternal. Re-entry conditions:

| Omitted item | Re-entry trigger |
|---|---|
| MCP server hosting | If Tier 2 unlocks AND user wants to expose AutoCode's tools to external Claude clients |
| GitHub webhooks | If user wants integration story (CI status comments, draft PRs from sessions, etc.) |
| Vector-based semantic retrieval | If MemoryFS scales past usable file-tree-grep performance (~10k+ topic files) |
| Multi-agent broker | If 3rd-party plugin ecosystem emerges around Tier 2 |
| Web UI | If a strong "remote operate" use case emerges (likely with Tier 2 unlock) |
| Cron tools | If User wants scheduled actions outside KAIROS |
| Replay/debugger | Already on Horizon 3E (Replay v2) - moves into "actively planned" once horizon shifts |

The rest (voice mode, Tamagotchi, anti-distillation, undercover mode, multi-agent Coordinator, LLM-decided "Auto Memory", Auto Dream) are deliberate "no" items - would need a strong user signal AND a competitive forcing function to reconsider.

---

## Maturity Tracks (Orthogonal Cross-Cut)

The phases above sequence by time; this section sequences by capability track. Reading by track is useful for "where is X going?"

| Track | v1 (now) | v2 (this pass close) | v3 (Horizon 1-2) | v4 (Horizon 3+) |
|---|---|---|---|---|
| Telemetry | JSONL emit + aggregator + CLI | CI gate strictness + drift->eval flywheel | Failure-class taxonomy + dashboards | Telemetry-driven auto-promotion |
| Memory | FS 3-layer + Path A compaction | Path B tuning + GC policies | Cross-project + pattern extraction | Personal fine-tune corpus |
| Eval | P1 hand-graded + substrate | P3d production runner + judge + flywheel | Multi-judge ensemble + qualitative criterion library | Auto-generation from sessions |
| Reliability | per-tool checkpoint + atomic rollback | Drift + PEV + Ralph + entropy (P3a/b/c) | Threshold calibration | Predictive failure detection |
| TUI | ~7500 LOC all surfaces wired | (P4a deferred) | Diff viz + inline streaming + session search | Multi-pane + tab/workspace |
| KAIROS | (P5 default OFF) | Opt-in default + dry-run | Trusted-env default | Multi-watcher fleet |
| Sandbox | Per-tool checkpoint + protected paths | (Tier 4.2 deferred) | (Tier 4.3 deferred) | Containerized execution |
| Hooks | HR foundation + 4 extracted | (HR-EXT-{1,2,3} deferred) | Plugin loading from user config | 3rd-party hook ecosystem (gated on Tier 2) |
| Cost | `--max-budget-usd` CI cap | - | Per-session caps + forecasting + cost-routing | Daily/weekly rollups + budget alerts |
| Multi-model | single model per session | - | Planner/Executor/Judge handoff | Recovery escalation path |
| Replay | none | - | (Horizon 3E) | Time-travel debugging |
| Distribution | uv + cargo | - | - | Single-binary + Homebrew + Docker |

---

## Trigger-Gated Unlocks

The roadmap branches at several explicit decision points. Each has a defined trigger:

| Item | Currently | Unblocks when | Goes to |
|---|---|---|---|
| TUI Path A refactor | Deferred | User says "ok pick up TUI now" | Horizon 1A |
| HR-EXT-{1,2,3} hook context | Deferred | User signals (or piles up enough mid-pass complaints about "two layers" in `agent/loop.py`) | Horizon 1B |
| Remaining harness follow-through | Mostly promoted to HFIX | HFIX/P3d closeout leaves legacy migration or broader-sweep gaps | Horizon 1C |
| KAIROS default-on | Default OFF | >=4 weeks P1a telemetry baseline + observability story | Horizon 2A |
| Tier 2 (P4) | Deferred | Concrete 2nd client OR `protocol.rs` >60 structs OR 2 concurrent backend consumers | Horizon 3A |
| Tier 4.2/4.3 | Deferred | Tier 2 unlocks (depends on it) | Horizon 3A |
| Vector retrieval | Deliberately omitted | MemoryFS scales past file-tree-grep performance (~10k topic files) | Horizon 4E |
| MCP server hosting | Deliberately omitted | Tier 2 unlocks AND user wants 3rd-party Claude clients | Horizon 4E |
| GitHub webhooks | Deliberately omitted | User wants integration story | Horizon 4E |

Pattern: never start a deferred item speculatively; wait for the trigger or explicit User direction. This is what made the "no TUI now" call clean - the trigger hadn't fired and User explicitly said "later."

---

## Hard "NO" List (Not On Any Horizon)

These are deliberate omissions per north-star with no projected re-entry condition:

- Voice mode.
- Multi-agent Coordinator.
- Buddy / Tamagotchi.
- Anti-distillation.
- Undercover mode.
- LLM-decided "Auto Memory" (file-system memory wins on legibility).
- Auto Dream advanced features.
- 5-tier compaction parity (Path A + Path B is enough).

Re-entry would require a strong forcing function (competitor differentiation, user-base pull, security mandate) AND explicit User redirection. Until then, every line of code spent on these is opportunity cost against the actively-planned roadmap.

---

## Risks & Cross-Cutting Dependencies

### Architectural Risks

1. Test surface growth - 2244 now -> projected ~2400 end of pass -> projected ~2800 end of Horizon 1 -> projected ~3500+ end of Horizon 2. CI runtime will start to bite around ~3000. Mitigation: pytest-xdist parallelization (low cost), test sharding (medium cost), or a tiered "smoke vs full" split (high payoff but design work).
2. LOC growth in `autocode/src/autocode/agent/` - `loop.py`, `factory.py`, `hooks.py`, `drift.py`, `prompts.py`, `tools.py`, `token_tracker.py`, `middleware.py`, `scratch.py`, `memory.py` (deprecated) - already 10+ files. Will likely need package reorganization around Horizon 1 (e.g. `agent/hooks/` subpackage with one file per concrete hook).
3. Telemetry baseline risk - KAIROS promotion is gated on >=4 weeks of baseline. If baseline is noisy (high variance in `kairos_action_blast_radius`, false-positive drift detections), promotion slips into Horizon 3. Mitigation: P1a observability is solid; risk is moderate, not severe.
4. Eval judge cost - eval suite v2 + v3 calls a strong judge model on every PR. At ~200 cases x ~$0.10/case = ~$20/PR x ~50 PRs/week = ~$1k/week if no sampling. Mitigation: P3d already mandates stratified sampling on PR (not all 200) + `--max-budget-usd 5.00` cap. Watch the ratio in production.
5. Drift->eval flywheel cold start - needs >=30 days of telemetry to seed. Until then, the eval library grows only by hand-curation. This is fine for Horizon 1; becomes a real input by Horizon 2.
6. Memory size at scale - `MEMORY.md` is currently 32 lines and the index design caps usefulness around 200. Topic files have no enforced cap. If session daily logs grow unboundedly, Layer 2 grep performance degrades. Mitigation: daily-log rotation policy + topic-file consolidation tool. Lands naturally at Horizon 3B.
7. TUI deferral risk - every tranche we defer P4a, the diff between current state and target state grows (adjacent code lands in the un-refactored layout). The widget-per-mode refactor gets harder. Mitigation: don't let too many tranches stack before TUI pass fires. Target: Horizon 1A within 4-8 weeks of pass close.

### Cross-Cutting Concerns That Constrain Everything

From `docs/plan/roadmaps/2026-04-30-tier-roadmap/05-cross-cutting-concerns.md`:

- First-turn latency invariant - every phase respects this (P1a `emit()` <5µs proves the discipline scales).
- No auto-rollback in verify pipeline - carried from C5.G4; never violated.
- Deterministic fixtures only - every harness scenario must be reproducible.
- No commits / pushes / tags by agents - durable rule, never relaxed.
- All agent comms via `AGENTS_CONVERSATION.MD` - durable rule.

These constrain HOW we build, not WHAT we build. They don't change across horizons.

---

## Visibility Limits - Where This Projection Runs Out

I'm confident through the end of Horizon 1 (~2-3 months out). Horizon 2 is medium-confidence - the work is scoped but the exact ordering depends on telemetry baseline accumulation rate and whether any deferred trigger fires unexpectedly. Horizon 3 is sketches based on current architecture trajectory; specific items will move based on user signal. Horizon 4 is speculative - I list items because the trajectory points there, not because they're decided.

What I cannot see clearly:

- User's strategic interest in third-party adoption (gates Tier 2 + MCP + Web UI).
- Whether AutoCode stays single-user or grows to team usage (gates collaboration story).
- Pricing/cost pressure on the eval suite (gates eval v3 architecture choices).
- What competitive forcing functions emerge (could pull "deliberately omitted" items into scope).
- What new Anthropic API features land 2026-Q3+ (could obviate planned work or open new tracks).

What's decided regardless:

- Sensors-first doctrine continues (telemetry-driven everything).
- Local-first defaults continue.
- File-system as canonical state continues.
- TDD discipline continues.
- Multi-agent comms via single log continues.

---

## TL;DR For The Next 6 Months

```text
Now (week 0)         : HFIX AI verification harness fixes before P3b
Week 1-2             : P3b PEV+Ralph, then P3c entropy + P3d eval suite
Week 2-3             : P5 KAIROS (default OFF) + final batch APPROVE
Week 3               : User commits stable codebase (Option C close)
─────────────────────────────────── stable commit boundary ───────────────────────────────────
Week 4-6             : TUI Path A refactor pass (~7500 -> ~4600 LOC)
Week 6-7             : Hook-context extension pass (HR-EXT-{1,2,3})
Week 7-8             : Post-HFIX harness follow-through if closeout left gaps
Week 8-12            : KAIROS baseline accumulation (telemetry watch)
Month 3              : KAIROS v2 opt-in default + eval suite v3 begins
Month 4-5            : Failure-class taxonomy + reliability v2 calibration
Month 6              : Drift->eval flywheel proven (>=10 cases generated/30d)
                       Tier 2 unlock decision check-in (likely still deferred)
```

Beyond month 6: depends on triggers and User signal. The roadmap is built to accept new direction at any phase boundary.
