# NEW_PLANS_REST_AUDIT.md — Audit of the *rest* of `new_plans/`

**What this covers:** the documents the two prior audits (`NEW_PLANS_GAPS.md`,
`NEW_PLANS_REMAINING_TODO.md`) **did not** touch. Those two audited PLAN_01–05
**against their own prose**. This one audits the **source material those plans
were distilled from**, plus the cross-references and repo state:

- `harness_copy_teacher/` — the 11-file **Anvil** program (research + build plan
  behind PLAN_04 teacher / PLAN_05 copycat).
- The loose **ClipMind** security stack (`00-adversarial-validation.md`,
  `01-trust-domains.md`, `01-phase-plan.md`, `02-open-questions.md`, `README.md`)
  — source behind PLAN_02 video-agent.
- The loose **autocode-station** stack (`autocode-station-requirements.md`, the two
  HTML mockups, `market-research-agent-cockpit (1).md`) — source behind PLAN_03.

**Method:** four read-only passes, each cross-referencing a source cluster against
the matching PLAN, the prior audits, and live repo state under `autocode/anvil/`,
`video-agent/`, and `harness-ide/crates/station/`. No files changed, no git writes,
no tests run.

---

## 0. The blind spot the prior audit had (read this first)

The prior audit measured each plan against itself. That makes **silently-dropped
scope invisible**: where a source doc specified something and the PLAN quietly left
it out, the prior audit had nothing to compare against and reported no gap. Every
"NOT captured" below is exactly that — specified in a source doc, absent from the
plan **and** absent from the repo.

Two prior-audit results also need correcting against current repo state:

- **Stale `❌`s:** prior audit marks the G5 distiller, the `teacher sense` command,
  and copycat **Channel B** as absent. They are now **built** (§6). Don't re-scope them.
- **Optimistic closure:** prior audit marks PLAN_04 / PLAN_05 **"Closing Gate A
  CLOSED."** That closure rests on a measurement substrate that does not exist
  (held-out corpus) and a gate that does not enforce the edge-cost guards it claims
  (§1, item 1). By the Anvil plan's own Phase-1 "do not proceed past this gate" rule,
  Gate A is **not** actually met.

---

## 1. Anvil program (`harness_copy_teacher/`) — never audited before

The teacher leg (PLAN_04 Phase 2) and copycat Channel A (PLAN_05 Phase 4) are
substantially **built and tested** (`autocode/src/autocode/anvil/`, ~6,146 LOC, 30
files, 5 patch bundles). The **self-maintenance engine (doc 07)** and the
**evaluation flywheel (doc 08)** are the genuinely uncaptured scope — and they are
the half that makes the "self-maintaining" claim true.

### 1.1 The dangerous middle state — built but not enforced

1. **Edge-cost guards are written but NOT WIRED into the live gate.** `cost.py`
   fully implements L4/latency/token measurement + `EdgeCostVerdict`. But the CLI
   gate call (`anvil/cli.py:282`) never passes `edge_cost_verdict`, so `gate()`
   records `edge_cost_measured: False` (`gate.py:114-119`) and silently degrades to
   *"tests passed ⇒ no regression."* **Every promoted bundle's
   `prediction_score.json` and audit-log entry therefore asserts "no edge-cost
   regression" that was never measured.** This is the single highest-ROI fix in the
   whole audit: the machinery exists; it's a few lines to measure baseline-vs-
   candidate trajectories and pass the verdict. *(This refines the prior audit's
   "edge-cost guards never measured" — they ARE computed, just not connected.)*

2. **No held-out corpus / eval split (gap G4).** Doc 08 §8.6 makes this the
   prerequisite for trusting *any* patch bundle; the roadmap (`09:32`) calls it "the
   most important [gate] in the program." There is no `corpus build`, no
   `held_out`/`train` split, no `eval` command, no measured noise band anywhere in
   `autocode/anvil/`. **Yet 5 bundles are already gated and promoted** on single test
   runs — the exact overfit-to-your-own-eval failure doc 08 warns about.

3. **Falsifiable prediction contract is a templated string, not a measurement.**
   Written by `propose.py:215` / `loop.py:212`, scored into `prediction_score.json`,
   but the "scoped claim on a held-out slice" is never checked against a slice
   (because there is no slice — see #2). The dedicated contract scorer `score.py` is
   absent.

### 1.2 Absent in code (the autonomous half of doc 07)

4. **Gate-component lockout test — absent.** Doc 07 §7.2 / risk-doc `10:49,88` name
   this "the single most important rule": an assertion that **fails the run if a
   patch bundle targets the verifier / eval suite / metrics / registry / kill
   switches.** It exists only as a docstring (`registry.py:9`). This is the one
   structural defense against the program's #1 risk — a self-modifying system editing
   its own oracle — and no plan assigns it.

5. **Kill switches — absent.** Doc 07 §7.3 specifies 8 triggers (held-out drop, L4
   spike, calibration drift, tripwire, gate-component target, ≥3 reverts, cost cap,
   wall-clock). `killswitch.py` does not exist; grep finds zero hits. PLAN_04 §4.7
   lists it as a Phase-6 checkbox only.

6. **Rollback / auto-revert — absent.** `promote.py` flips `status=promoted` and
   writes the audit line but performs **no `git apply`** and offers **no revert
   path**; there is no `enabled_bundles` flag and no auto-revert window. "git revert is
   always available" (`loop.py:201`) is manual operator action, not code.

7. **Canary / shadow promotion — absent.** Doc 07 §7.4 wants shadow-first + flagged
   promotion + auto-revert window. Promotion is immediate; `canary.py` does not exist.

8. **Statistical rigor — absent, and not even on the TODO list.** Doc 08 §8.3 (k≥3
   replication, paired comparison, measured noise band, significance gating, pass@k vs
   pass^k) is the rigor that "prevents promoting noise." The verifier runs **once** per
   case (`verifier.py:159`). Doc 08 §8.3 is the **most fully-uncaptured spec in the
   set** — no module, no plan bullet, no TODO box.

9. **Prediction-calibration meta-signal — absent.** Correction 8 (`01:154`,
   `04:232`): systematic prediction misses ⇒ the loop's judgment is miscalibrated ⇒ a
   kill trigger *independent of eval scores*. The repo writes `prediction_score.json`
   but nothing aggregates miss-rate into a loop-health signal. Small to add; turns an
   existing data stream into the safety signal it was meant to be.

### 1.3 Structurally uncaptured scope

10. **The true G1 harness-component manifest doesn't exist.** Doc 04 §40-98 specifies
    a 7-kind AHE manifest (system_prompt / tool_impl / middleware / skill / subagent /
    memory) with `prediction_metrics` + `edit_surface` fields. The file that exists,
    `manifest.py`, introspects the **CLI flag/subcommand surface** for copycat gap-diff
    — a same-named decoy. Consequence: copycat/teacher proposals **cannot be scoped to a
    manifest entry's legal claim space** (05 §5.1.3), so the contract's "scoped" property
    is unbacked.

11. **GEPA (tier-4 prompt optimizer) silently deleted.** Correction 2 said *demote it,
    don't delete it* ("tier 4, not the headline" — `01:49,52`). The plans dropped it
    entirely: zero `gepa`/`dspy` references, no phase, no TODO box (`04:81,278`). The
    tier-4 rung of the escalation ladder is unimplemented and unowned.

12. **Phase 0 design doc `docs/research/anvil-design.md` was never written.**
    `09:13-17` makes it the program's *first* exit gate — the invariant-legality check a
    north-star reviewer would block on. It does not exist on disk. ~1 day, cheapest
    unstarted item.

13. **ACE Pruner merge is not prediction-gated.** Doc 06 §6.3 / PLAN_04 §4.3 require the
    playbook prune to itself be a contracted change ("does pass@1 hold after pruning?").
    The `prune` command (`teacher/cli.py:313`) is an unguarded rewrite — the one ACE-
    discipline corner cut.

14. **Marquee targets unbuilt:** the **Ralph loop** (PLAN_05's named first Channel-A
    target — `grep ralph` → 0) and the **Terminal-Bench** external yardstick (doc 08's
    only honesty check against your own corpus — `terminal_bench.py` absent). Until
    Terminal-Bench exists, "guards against overfitting to your own eval" is unenforceable.

---

## 2. ClipMind security stack — never audited before

The one structural win survived and is real; the defense-in-depth around it is mostly
vapor. The video-agent component (`video-agent/src/video_agent/`) implements PLAN_02.

### 2.1 Built and solid — the load-bearing barrier

- **Proposer/compiler split is genuinely built.** Closed, typed op grammar with
  `extra="forbid"` so no `shell`/`path`/`command` can be smuggled
  (`schema/change_request.py:16-19,172-192`); non-LLM authorization chokepoint
  (`compiler/validate.py:56-149`); untrusted LLM output funnelled through the schema
  gate (`agent/planner.py:111-131`); tests prove rejection (`tests/test_schema.py:31`,
  `tests/test_validate.py`). **This alone breaks the canonical OCR→exfil chain** — the
  planner literally cannot express exfiltration. Of the source docs' "four independent
  barriers," two (b: no exec/file op; c: no export op in schema) are real and structural.

### 2.2 The other two barriers + the defense-in-depth — NOT built

| Concern (source anchor) | In PLAN_02? | Built? | Note |
|---|---|---|---|
| **Egress gate** — deny-by-default + approval (`01-trust-domains.md:48`; barrier *(d)*) | named "simpler" | **NO** | The cloud planner already ships (`cli.py:27-45`, `--planner llm`) and sends the Bundle to OpenAI with **zero gating**. The one structurally-absent link in the exploit chain. |
| **Redaction pass** (`00-adversarial-validation.md:104`) | named (Phase 4) | **NO** | `bundle.py:43-45` inlines raw transcript text. No PII masking. |
| **Instruction/data separation** — barrier *(a)* (`01-trust-domains.md:34`) | implicit | **NO** | Only a system-prompt sentence (`planner.py:97`); untrusted text shares the prompt blob. |
| **Per-derivative sensitivity + retention** (`00-adversarial-validation.md:51` — "most insightful point") | not carried | **NO** | Single scalar `sensitivity` (`change_request.py:203`); no retention reaper. |
| **Adversarial test corpus** — injection C7 + redaction C4 (open-Q8) | not owned | **NO** | One shell-field rejection test only. The injection-resistance claim is asserted, never demonstrated. |
| **Capture isolation** (evdev broker) | **dropped by design** | N/A | Defensible — PLAN_02 edits user-supplied footage, never records. Record this as a *decision*, not an oversight. |
| **Host hardening / logging hygiene** | Phase-6 deferred | **NO** | Rootless/`--network=none`/SBOM never reached. |

### 2.3 Decisions taken by omission (open-questions doc)

- **Q1 — cloud mode wanted?** The repo shipped *both* planners but took the riskier
  cloud fork **without** the egress gate Q1 says it requires.
- **Q2 — logical-only isolation acceptable?** Repo assumed yes; never confirmed.
- **Q8 — adversarial corpus before shipping?** Repo built none.

---

## 3. autocode-station stack — never audited before

PLAN_03 §9 *lists* the requirements-doc surfaces as "carry forward" but never re-specs
them. Result: of **21 hard requirements, 6 are absent from PLAN_03's body entirely**
and **8 more are placeholder/label-only in the repo** despite being P0/P1. Repo:
`harness-ide/crates/station/` (8-view `View` enum, `app.rs:16-25`).

### 3.1 Specified but absent from PLAN_03 body *and* repo

- **R2 Workstreams 3-pane** (list │ timeline │ review-rail) — PLAN_03 folded it into the
  Editor view; the timeline/review-rail has no home.
- **R7–R9 Collaboration** — presence/roster/follow-mode, shared file:line review
  comments with "Send to agent". Zero code. PLAN_03 §3.3 substitutes Zed's generic CRDT,
  which is **not** the requirements doc's presence/maker-checker model.
- **R15 Status model** — ~20 states → Inbox-bucket mapping. No plan owns the enum; repo
  has ~6 ad-hoc statuses.
- **R17 Browser-QA split** — Preview Browser vs Chrome Bridge, per-domain perms,
  **untrusted-context** label. Security-sensitive; repo view is a placeholder.
- **R18 New-Task wizard** — intent-first → prompt → context → execution → preview. The
  primary task-creation flow; absent from plan and repo (composer only).

### 3.2 P0/P1 requirements that are placeholder/label-only in the repo

- **R13 Merge-gate (P0)** — entirely a diff dump (`app.rs:981-995`); no checklist, no
  block-with-reason, no override, no "Ready to ship". *Highest-ROI station item.*
- **R4 Ask-why hunk affordance (P0 sub-item)** — Accept/Reject exist; Ask-why has no UI
  (one button + agent round-trip).
- **R10 Maker/checker** — `requires_checker` is shown as a label (`app.rs:354`) with no
  role identity and no delegation.
- **R1 Inbox default** — default view is `View::Editor` (`app.rs:169`), not the
  attention-first Inbox the spec mandates. One-line fix.
- **R12 Approval scope** — only "Approve once / Deny"; missing "Approve test commands
  for this task" (and the spec deliberately *rejects* "approve for session").
- **R14 Audit log** — tail rendered; no filters, no JSONL export (the named commercial wedge).
- **R20 Compare** — races harnesses but has no scorecard / cherry-pick / archive-losers.

### 3.3 Market-research positioning dropped

The research's thesis — *"don't launch as another wrapper; launch as the governed one
that runs on Linux"* — makes the merge-gate, governance, secured browser, and remote-auth
**the product**, not polish. PLAN_03 inherited the framing but deferred the surfaces:

- **Secured remote web access + token auth from day one** — research risk #4, "fatal
  impact." **No auth model in any plan.** PLAN_03 is desktop-first; web is "a remote-client
  option." Launch-blocking for the Linux/web play.
- **Governance policy *editor* + org/team admin + on-prem** — the only monetizable surface
  (research §S2); PLAN_03 has audit + maker/checker but no policy editor.
- **v2-mockup casualties:** the Skills view, voice input, and `@files`/`/skills` composer
  affordances were silently dropped when PLAN_03 followed the v3 mockup.

### 3.4 The two mockups diverge in *scope*, not just layout

`codestation-mockup-v2` is a 4-view threads-first product; `autocode-station-v3` is the
8-view governed product matching the requirements doc. **PLAN_03 + repo followed v3.**
One residual conflict: requirements §8 scopes collaboration to *modelled presence*
("conflict-free merge engine is a later concern") while PLAN_03 §3.3 lists *full Zed CRDT*
— an unresolved scope conflict, not a coverage gap.

---

## 4. Doc-integrity gaps

- **The ClipMind `README.md` document-map is ~93% aspirational.** It advertises a
  6-section, ~28-file nested tree; **26 of 28 files do not exist on disk** (the directory
  is flat with 4 plan files). Missing include *all five* deep security specs
  (`02-security/01-threat-model` … `05-host-hardening`) and the
  `00-overview/01-executive-summary.md` that the README itself tells you to "read first."
  Live source docs cross-reference these vapor files for "the detail." Either write them
  or rewrite the map to the flat 4-file reality and kill the dead links.
- **The Anvil `manifest.py` is a same-named decoy** for the real G1 harness-component
  manifest (§1, item 10) — a naming collision that masks an unbuilt component.

---

## 5. Unowned decisions (consolidated `[DECIDE]` list for the user)

These need a human call; no plan surfaces them. Most are near-zero engineering cost and
they *bound scope* downstream.

**Anvil (`10_RISKS…`):**
1. **Tool vs research artifact** — stop at ~Phase 4 (≈80% of value per `10:59`) or push to
   Phases 5–7? No plan states a stopping point, so 5–7 read as table-stakes.
2. **Autonomy cap + "Anvil may not create new planning docs"** (`10:51`) — the mitigation
   for process-overhead explosion; unowned.
3. **Default `reuse_scope` + a `tos-check` CLI command** (`10:32`) — the registry enforces
   `tos_check` presence but no command records one, so the `weights` scope is permanently
   un-runnable (safe-by-default, but untested).
4. **Harness-only vs rented-GPU distillation** (`10:19`) — gates whether Phase 7 is in scope
   at all. Constraint to record: RX 480 is not a trainer (ROCm dropped Polaris); the 8GB
   4060 Ti is the only trainer and QLoRA on 8B is "marginal-to-infeasible."
5. **Codename "Anvil"** — already baked into `autocode anvil …` and `src/autocode/anvil/`;
   locked-in-by-default without ever being decided.

**ClipMind:** Q1 (cloud mode + its required egress gate), Q2 (logical-only isolation OK?),
Q8 (build the injection + redaction corpus?).

**Station:** approve-for-session taxonomy; Skills-view fate; voice/image input; Workstreams
as a view vs folded; CRDT depth (presence-only vs full CRDT — the §3.4 scope conflict);
web/remote auth architecture; status-model state-machine ownership.

---

## 6. Verified already-done — do NOT re-flag from prior audits

- **Anvil teacher leg:** signal hierarchy, root-cause taxonomy + classifier, ACE playbook
  (generator/reflector/curator/pruner), trajectory recorder, deterministic verifier — built
  + ~13 unit tests (`teacher/*.py`).
- **Anvil G5 distiller + `teacher sense`** — built (`teacher/distill.py`, Layer 0–3). Prior
  audit's `❌` at `NEW_PLANS_GAPS.md:637` is **stale**.
- **Copycat Channel B (outcome eval) + dataset render + `outcome`/`distill` CLI** — built
  (`copycat/outcome.py`, `copycat/distill.py`). Prior "Channel B ABSENT"
  (`NEW_PLANS_GAPS.md:679`) is **stale**.
- **`reuse_scope: weights` + ToS-gate enforcement** — built (`registry.py:84-103`).
- **Edge-cost *measurement* logic** — built (`cost.py`); only the *wiring* into the gate is
  missing (§1, item 1).
- **ClipMind proposer/compiler barrier + closed op grammar + sensitivity check** — built and
  tested (`video-agent/`), §2.1.
- **Station Editor / inline-edit (`Ctrl+I`) / hunk Accept-Reject / approval-card risk
  framing / Compare-race** — built (`editor.rs`, `app.rs:291-387,1098-1163`).

---

## 7. Prioritized remaining-work roll-up (cross-cluster, by ROI)

**Tier 1 — small fix, removes a false-green or launch blocker:**
1. **Wire `edge_cost_verdict` into the live Anvil gate** (`cli.py:282` → `gate.py:114`).
   Machinery already exists; until done, every promoted bundle's "no edge-cost regression"
   is false. *(§1.1)*
2. **Egress/approval gate around the ClipMind cloud planner** (`cli.py:27-45`). The only
   structurally-absent link in the OCR-exfil chain; small code. Resolves open-Q1. *(§2.2)*
3. **Station merge-gate view (R13, P0)** — checklist + block-with-reason + typed-note
   override + commit/PR enable. The one P0 that is a pure diff dump. *(§3.2)*
4. **Station: Inbox-as-default + `Ctrl 1-4` view nav** — one-line default change + 4 palette
   bindings. *(§3.2)*
5. **Anvil gate-component lockout test** — fails the run if a bundle targets the
   verifier/eval/registry/metrics. The "single most important rule," currently a docstring.
   *(§1.2, item 4)*
6. **Anvil prediction-calibration aggregation** — turn the existing `prediction_score.json`
   stream into a miss-rate / kill signal. *(§1.2, item 9)*

**Tier 2 — the trust substrates the plans claim but don't have:**
7. **Anvil held-out corpus + `eval` command + measured noise band (G4)** — the Phase-1 "do
   not proceed" gate; unblocks #1 being trustworthy and de-optimisms "Gate A CLOSED." *(§1.1)*
8. **Anvil statistical rigor (08 §8.3)** — k≥3 replication, paired comparison, significance
   gating. The wholly-uncaptured spec. *(§1.2, item 8)*
9. **ClipMind injection (C7) + redaction (C4) adversarial corpus** — converts the security
   claim from asserted to demonstrated. *(§2.2)*
10. **ClipMind instruction/data separation + Bundle redaction** — fence untrusted evidence in
    a typed field, PII-mask before egress. *(§2.2)*
11. **Station shared-review comments → "Send to agent" (R9, P1)** + **Browser-QA split with
    untrusted-context quarantine (R17, P1)**. *(§3.1)*
12. **Resolve the §5 decision list** (esp. Anvil tool-vs-artifact, autonomy cap; ClipMind Q1/Q8;
    Station web-auth + CRDT-depth). Near-zero cost, bounds everything below.

**Tier 3 — larger, gated on a decision above:**
13. **True G1 AHE component manifest** (distinct from the CLI-census decoy) — unblocks scoped,
    falsifiable copycat/teacher proposals. *(§1.3, item 10)*
14. **Anvil autonomy primitives** — kill switches, canary/shadow, `promote` actually
    `git apply` + auto-revert window. Required before any "self-maintaining" claim. *(§1.2)*
15. **Anvil GEPA tier-4 optimizer** — build it or formally drop it (Correction 2 said demote,
    not delete). *(§1.3, item 11)*
16. **Station Workstreams 3-pane (R2) + New-Task wizard (R18) + status-model state machine
    (R15) + presence/governance policy-editor** (the named commercial differentiators).
17. **Anvil Terminal-Bench external yardstick + distillation trainer (Phase 7)** — gated on the
    tool-vs-artifact decision. *(§1.2, item 14; §1.3)*
18. **Doc hygiene:** fix the ClipMind README map (write or delete the 26 missing files);
    rename or build the real Anvil manifest. *(§4)*
19. **Write Phase-0 `docs/research/anvil-design.md`** — the program's north-star-legality gate.
    *(§1.3, item 12)*

---

## 8. Cross-cutting gaps spanning the whole corpus

These span *all* the source clusters, so no per-cluster pass surfaced them. All three are
verified against repo state.

1. **The same "untrusted-proposes / trusted-authorizes" barrier is reinvented three
   times.** ClipMind's proposer/compiler (`video-agent/compiler/validate.py`), the station's
   approval gate + maker/checker (`harness-ide/crates/station/src/approver.rs`), and Anvil's
   patch-bundle gate + registry (`autocode/anvil/{gate,registry,promote}.py`) are three
   independent implementations of one pattern — across two languages. *No single plan owns
   the shared authorization model.* Not a call to force a premature abstraction (cross-language
   makes a shared lib non-free) — but the **threat model, audit-log format, and approval
   semantics should be specified once and referenced**, or the three will drift (e.g. ClipMind
   already has no egress gate while the station has a full risk-framed approval card for the
   same class of action).

2. **Producer↔consumer schema contract for trajectories is unowned.** Anvil's eval flywheel
   (docs 04/08) depends on the runtime emitting trajectories; the recorder consumes a
   `layer_distribution` field (`teacher/recorder.py`). But **PLAN_01 (the harness-ide that is
   the runtime) mentions trajectories / `layer_distribution` zero times.** The flywheel's data
   *producer* never commits to the *consumer's* schema. This is the kind of integration gap
   that passes every per-component test and fails the moment the loop runs end-to-end. Owner
   needed: a single trajectory-schema contract referenced by both PLAN_01 and the Anvil docs.

3. **`new_plans/` has no master index of its own contents.** `README.md` describes *only*
   ClipMind and mentions PLAN_01–05 **zero times**; the only index file
   (`harness_copy_teacher/00_INDEX.md`) covers *only* Anvil. So the five PLANs + Anvil +
   ClipMind + station coexist with **no top-level map tying them together or stating their
   dependency order** (e.g. Anvil needs PLAN_01's trajectories; PLAN_03 station shares the
   harness-ide crate with PLAN_01). Combined with the 26 missing README-advertised files (§4),
   the directory's own navigation is the weakest-documented part of the corpus. Cheapest fix
   in the audit: one top-level `INDEX.md` (5 PLANs + Anvil + ClipMind + station, with the
   producer/consumer and shared-crate dependency edges) — and either repair or retire the
   ClipMind README map.

*(`harness_copy_teacher/REFERENCES.md` was checked and is a pure citation list — 39 sources,
nothing actionable.)*

---

## 9. Empirical implementation & test status (suites actually run, 2026-06-23)

§1–§8 classified built/partial/absent from source. This section is the empirical layer:
the test suites were **run**, not read. Distinguishes *implemented* (code written) from
*working* (covered by a passing test).

### Scoreboard

| Component (plan) | Test command | Result | % implemented | % working (tested) |
|---|---|---|---|---|
| **harness-ide engine** (PLAN_01) | `cargo test --workspace` | compiles clean; **65/65 green** | ~90% | ~90% |
| **station GPU IDE** (PLAN_03) | (same workspace; 26 station tests incl. 2 real wgpu UI) | green; **6/8 views real**, 2 placeholder | ~70% | ~60% |
| **video-agent** (PLAN_02) | `.venv/bin/python -m pytest` | **112 passed, 1 skip, 0 fail** | ~60% of full spec | ~95–100% of built |
| **Anvil teacher+copycat** (PLAN_04/05) | `pytest -k "anvil or teacher or copycat"` | **200/200 unit green**; 1 live-e2e flake | ~80% (thru Phase 4) | ~75% |

No environment blockers: the Rust workspace built in 30s with GPU available (the station's
headless wgpu render tests actually executed); ffmpeg+ffprobe present so all 16 video-agent
e2e tests did **real renders** including a frame-identical (framemd5) determinism check; the
LiteLLM gateway + `puku-cli` were live so the one Anvil e2e ran for real. **Across all four
components there is exactly one failing test, and it is a local-model behavioral flake, not a
code defect** (the teacher loop ran end-to-end and produced a valid packet; the local model
returned an empty student trajectory — consistent with the known local-model tool-calling
caveat). Every other red is zero.

### What's genuinely working (built + green)

- **PLAN_01 harness-ide:** the whole engine substrate — 40+ MCP tools (fs/grep/run/git/LSP via
  a real rust-analyzer JSON-RPC client/browser/session), permission model (profiles,
  read-before-edit, plan-mode, approval scopes, policy rules — 12 approval unit tests),
  session lifecycle (pending hunks apply/discard + audit), a diffy-backed **semantic 3-way
  merge** (the R13 substrate), and MCP stdio+HTTP transports. ~90% working.
- **PLAN_03 station:** a real native GPU IDE shell — Editor (tree/tabs/syntax/find-replace/⌘I
  inline-AI/**Accept-Reject hunks** through the real engine), Inbox, Search, Compare (multi-
  harness A/B race), Settings (capability matrix + immutable audit log), plus always-on agent
  streaming panel, run panel, command palette, and the risk-framed modal approval card. 6 of 8
  views are real.
- **PLAN_02 video-agent:** the proposer/compiler safety barrier (closed 16-op grammar with
  `extra="forbid"`, non-LLM `validate.py`, LLM output re-parsed through the same gate — 14
  validator + 6 schema tests) and the full deterministic FFmpeg/timeline render pipeline
  (19 codegen + 16 e2e tests, real renders). 95–100% of what's built is tested.
- **Anvil:** the entire build→validate→promote loop (registry-gate → census → gap-diff →
  propose → gate → promote → append-only audit) and teacher online path (recorder, verifier,
  signal, cost, classifier, taxonomy, reflector, ACE playbook, distiller) — every one of 28
  modules has a passing test file. Copycat Channel A and Channel B (outcome + ToS-gated distill
  dataset) are production-shaped and tested (22 Channel-B tests green).

### Remaining to IMPLEMENT (code not written) — ranked, cross-component

1. **Wire `edge_cost_verdict` into Anvil's live gate, and make `promote()` block on
   `no_regression` not just `met`.** Empirically confirmed *worse* than §1.1 said: not only does
   `cli.py:282` omit the verdict (→ `edge_cost_measured:False`, `no_regression` defaulted True),
   but `promote.py:43-49` gates on `score["met"]` (tests-passed) and never consults
   `no_regression` — so the program's core "edge cost can't regress" invariant **cannot block a
   promotion today**. Code exists; it's wiring + one guard line. *Highest ROI in the repo.*
   *(Verified at source: `promote.py:42` raises only on `not score["met"]`; `no_regression` is
   recorded in the audit entry at `:58` but never gated on — and the module docstring `:3-4` claims
   promotion requires "no edge-cost regression," so the code enforces less than it documents.)*
2. **station Review merge-gate (R13).** Review is a read-only colored diff (`app.rs:981-995`); the
   `semantic_merge` substrate is already built and tested in the engine — the UI to consume it
   (per-hunk accept/comment, commit checklist + override) is the missing piece. Highest station ROI.
3. **station maker/checker *enforcement*.** Today `requires_checker` is display-only, set
   `Some(..)` only in a test fixture (`app.rs:1392`); the real approval path always sets `None`
   (`approval.rs:422`). Need the policy decision (set it on high/critical risk) + a `maker ≠ checker`
   identity check.
4. **video-agent egress/redaction trust boundary.** Zero code despite the README's safety claim;
   the cloud planner already ships ungated. (= §2.2 / §7-Tier-1 item 2.)
5. **Anvil safety/hardening for autonomy:** kill switches, canary promotion, gate-component
   lockout, held-out corpus/eval split — all empirically confirmed absent (greps return nothing).
   Prerequisite for any "self-maintaining" claim.
6. **station BrowserQA + Automations views** (both route to `placeholder()`); **video-agent
   ASR/OCR/VLM perception**, **Remotion backend**, **local/cloud planner router**; **Anvil GEPA
   tier-4 + distillation trainer**. The larger, lower-urgency build-out.

### Remaining to TEST (code written, no/weak/flaky coverage) — ranked

1. **Anvil teacher live loop** (`teacher/loop.py`) — the only red; needs a deterministic
   stubbed-gateway test so correctness isn't hostage to local-model behavior. `teacher/gateway.py`
   (74 LOC) has no offline unit test either.
2. **station behavioral UI tests** — the wgpu tests only assert "renders without panic" across all
   8 views; nothing drives Accept/Reject, the palette, or the approval-card click path through
   simulated events. No snapshot baselines committed (visual regressions uncaught).
3. **video-agent live-LLM planner** (1 skip, 0 active tests) and **scene detection** (parser-only,
   no manifest-level assertion); CLI llm path is `# pragma: no cover`.
4. **Anvil CLI edge-cost/promote gating** — once item-1-to-implement lands, needs a test asserting a
   regressing verdict blocks promotion (none exists).

### Bottom line

**Combined: ~75% implemented, ~70% working-with-tests across the four components.** The
deterministic, safety-critical cores are real and well-tested — the PLAN_01 engine, the
video-agent proposer/compiler + FFmpeg pipeline, and the Anvil build→promote loop all stand on
green suites with real renders/gateway runs. The missing quarter is concentrated and well-defined:
**(a)** two enforcement gaps where the mechanism exists but isn't active — Anvil's edge-cost guard
(unwired) and the station's maker/checker (label-only); **(b)** stubbed surfaces — station
BrowserQA/Automations/merge-gate UI; **(c)** the optional heavy layers — video perception/Remotion,
Anvil autonomy + training. The single most valuable next move is not new features but **activating
the two already-built guards** (items 1 and 3 above).
