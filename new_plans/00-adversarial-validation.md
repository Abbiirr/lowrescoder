# Adversarial Review — Validation, Claim by Claim

This document validates the uploaded adversarial security review (`deep-research-report__17_.md`) against primary sources and engineering reality. The purpose is to absorb what's correct, push back on what's overstated, and avoid building on any claim that doesn't hold. The review is **largely sound and worth adopting** — but a few points need calibration so the final design is honest, not just maximally paranoid.

**Verdict up front:** The review's central thesis — *the original plan collapses trust boundaries onto one host, and the planner has too much power* — is correct and well-supported. Its proposed fix (planner proposes, policy compiler authorizes; isolate privileged capture; deny-by-default egress) maps onto a real, citable security pattern. Adopt the core. Calibrate the severity ratings and the implementation cost for a solo internal tool.

---

## Claim 1 — "Trust-boundary collapse is the main problem." ✅ VALID, adopt

The review argues that putting privileged capture, perception, planning, shell access, and rendering on one host wired through agent tooling means one compromise reaches everything.

**Validation:** This is correct and is the strongest point in the review. The original plan did exactly this — the MCP server had `Bash` in `allowed-tools`, the planner could read project files, and the evdev capture lived in the same toolchain. OWASP's LLM01:2025 guidance explicitly says to "treat the model as an untrusted user to test the effectiveness of trust boundaries and access controls" and to "implement human-in-the-loop controls for privileged operations." The collapse is real.

**Adopt:** Yes. The five-trust-domain split (`01-architecture/01-trust-domains.md`) is the right response.

---

## Claim 2 — "Indirect prompt injection via OCR / transcript / images is a critical risk." ✅ VALID, adopt

The review argues that OCR text, transcripts, on-screen terminal content, and even pixels in a contact sheet are untrusted data that can carry instructions into the agent loop.

**Validation:** Fully supported by primary sources. OWASP's Prompt Injection Prevention Cheat Sheet describes the canonical attack (a document containing "IGNORE ALL PREVIOUS INSTRUCTIONS…") and recommends the **dual-LLM pattern** (Simon Willison's design, now in the OWASP cheat sheet): a *privileged* LLM that holds tools but never reads untrusted content, and a *quarantined* LLM that reads untrusted content but cannot act. DeepMind's CaMeL framework (March 2025) is the same idea formalized: "treat the LLM as a fundamentally untrusted component." OWASP LLM01:2025 explicitly calls out multimodal injection as a rising risk. The threat is not hypothetical for *this* tool specifically, because the whole job is ingesting screen recordings that frequently contain terminals, chat windows, and documents — i.e. attacker-controllable text and pixels by construction.

**Calibration:** The *probability* for a single-user internal tool editing *your own* footage is lower than for a public multi-tenant agent — you're not ingesting adversarial uploads from strangers. But the *impact* (NDA'd footage exfiltration) is high, and "my own footage" includes screen-shares of third-party sites, support tickets, and customer data you don't control the contents of. So: real risk, slightly lower likelihood than the review implies, high enough impact to justify the defense. Adopt.

---

## Claim 3 — "Confused-deputy execution: a powerful planner + powerful tools = one injection from disaster." ✅ VALID, adopt

**Validation:** Correct. OWASP is explicit that a guardrail LLM "is itself susceptible to prompt injection" and is "one layer in a defense-in-depth design, not a replacement for input validation, structured prompts, least-privilege tool scopes, or human approval." The original plan's hooks (PreToolUse path-jail etc.) are a guardrail layer, not a sufficient boundary. The fix — convert the planner from an *actor* into a *proposer* that emits typed change requests, validated by a separate compiler — is exactly the privileged/quarantined separation applied to actions. Adopt.

---

## Claim 4 — "Docker group is root-equivalent; daemon runs as root; use rootless." ✅ VALID but standard

**Validation:** True and well-documented (Docker's own post-install and security docs). Membership in the `docker` group is effectively root because you can bind-mount the host filesystem into a container. Rootless mode is the correct baseline.

**Calibration:** This is correct but it's *standard container hygiene*, not a novel finding specific to this tool. Rated "High" in the review; for a solo workstation it's "do the normal rootless thing," not a project-defining risk. Adopt the recommendation (rootless workers, no docker-socket mounts), don't over-weight it.

---

## Claim 5 — "Capture-session persistence / stream misbinding on Wayland portals." ✅ VALID, useful catch

**Validation:** Correct and genuinely useful. `xdg-desktop-portal`'s ScreenCast docs do warn that PipeWire stream node IDs can be reused and that consumers should prefer the monotonic `pipewire-serial` for targeting; restore tokens can persist sessions. After monitor hotplug or suspend/resume, a stale pipeline can bind the wrong display — which for multi-monitor demo work means accidentally capturing the wrong screen. This is a real reliability+privacy bug class the original plan didn't address.

**Adopt:** Yes — handled in `03-components/00-recorder-and-capture.md` (re-validate stream target on every session; never reuse a restore token silently).

---

## Claim 6 — "Derivatives (OCR dumps, transcripts, contact sheets) are more exfiltration-friendly than the raw video." ✅ VALID, subtle and important

**Validation:** This is the most insightful point in the review and easy to miss. "Footage never leaves the machine" is necessary but not sufficient: a transcript or OCR dump is plaintext, grep-able, and small — far easier to exfiltrate or accidentally log than a multi-GB video. Privacy engineering (data minimization) cares about *how much derivative data exists and how accessible it is*, not just where the source sits. Adopt: derivatives get the same sensitivity labels, retention clocks, and egress rules as source (`02-security/04-egress-and-redaction.md`).

---

## Claim 7 — "Single-node / shared-GPU overload causes non-deterministic UX." ⚠️ VALID but over-stated for solo use

**Validation:** Directionally right. Running Qwen3-VL + WhisperX + FFmpeg/Remotion on one workstation with two 8GB-class GPUs *will* contend if scheduled naively. WhisperX large-v2 wants <8GB on its own; the VLM wants ~6GB; Remotion spins Chromium.

**Calibration:** The review frames this as a reliability *risk*; for a solo, non-realtime authoring tool it's a *scheduling task*, not a hazard. You don't need a distributed work queue on day one — you need a simple local job queue that doesn't run the VLM and WhisperX on the same card simultaneously. The dual-GPU split (VLM+Whisper on the 4060 Ti, OCR+FFmpeg VAAPI on the RX 480) plus serialized heavy stages solves it. Adopt a lightweight queue; don't build Kubernetes for one user.

---

## Claim 8 — "Underspecified: authn/authz, RTO/RPO, SBOM, signed builds, incident response, concurrency." ⚠️ VALID but partly scope-inflated

**Validation:** The review is right that the original plan didn't specify these. For a *deployable internal system serving a team*, they matter.

**Calibration:** For a **solo internal tool**, several of these are over-scoped:
- **authn/authz** — single user on their own workstation; OS-level user permissions suffice initially. Matters only if it becomes multi-user.
- **RTO/RPO / backup** — "back up the artifact store and the git repo of specs" is the whole story; formal recovery objectives are theater for one person.
- **SBOM / signed builds / SLSA provenance** — genuinely worth it *if regulated footage is in frame*, because you may need to prove the toolchain wasn't tampered with. Stage it (phase 6), don't gate the MVP on it.
- **Incident response playbooks** — a lightweight "suspected exfiltration" checklist is worth having; three formal playbooks on day one is overkill solo.

So: the review is correct that these were missing, but applying the full enterprise SDLC to a one-person tool is the opposite failure. The phase plan stages security to match actual risk exposure.

---

## Claim 9 — "16–24 engineering weeks for a security-hardened tool." ⚠️ REASONABLE for the hardened version, not the MVP

The review's own roadmap concedes "a fast solo prototype can be done sooner." Agreed. The MVP (perceive → propose → compile → render, with the recorder boundary and proposer/compiler split but *without* SBOM/signed-builds/multi-dashboard observability) is a few weekends, not 4–6 months. The 16–24 week figure is the *fully hardened* endpoint. Both are stated in `04-implementation/01-phase-plan.md` so you can choose where to stop.

---

## What the review got slightly wrong or under-weighted

1. **It under-credits how much the original plan already mitigated.** The original already had: spec-first (no media mutation), hard-metadata-over-vision (click events not pixel-guessing), per-edit human approval, and PreToolUse path-jail. The review acknowledges this but its severity table reads as if the original were a naive "agent drives Bash" design. The delta is "good prototype → deployable system," which the review does eventually say.

2. **It treats the external-model path as the main egress risk, but the bigger practical leak is logging.** Transcripts and OCR in plaintext logs, crash dumps, or a misconfigured telemetry library will leak before the planner ever calls an external model. Redaction + log hygiene matters as much as the egress gate.

3. **The Mermaid "policy compiler" can become its own complexity sink.** A typed Change Request validated against a schema + a sensitivity-label check is the 80/20. A full "policy DSL" is a tarpit for a solo build. `01-architecture/02-data-model.md` keeps the compiler deliberately small.

---

## Net adoption decision

| Review recommendation | Adopt? | Where |
|---|---|---|
| Five trust domains | Yes | `01-architecture/01-trust-domains.md` |
| Planner proposes, compiler authorizes (no shell to model) | Yes — core | `01-architecture/01`, `03-components/03` |
| Isolated recorder broker (narrow API, service account) | Yes | `03-components/00`, `02-security/03` |
| Quarantined vs privileged LLM / instruction-data separation | Yes | `02-security/02` |
| Content-addressed immutable artifact store + manifests | Yes | `01-architecture/02` |
| Deny-by-default egress + redacted external-model gate | Yes | `02-security/04` |
| Derivatives get source-equal sensitivity treatment | Yes | `02-security/04` |
| Rootless containers, no docker-socket mounts | Yes (standard) | `02-security/05` |
| Re-validate portal stream target; no silent restore-token reuse | Yes | `03-components/00` |
| Golden-corpus + adversarial test classes | Yes | `05-verification/*` |
| SBOM / signed builds / SLSA provenance | Stage to phase 6 | `04-implementation/01` |
| Formal RTO/RPO, multi-dashboard observability, 3 IR playbooks | Trim to solo-appropriate minimum | `04-implementation/01`, `05-verification/02` |
| 16–24 week timeline | True for hardened endpoint; MVP is far sooner | `04-implementation/01` |

The rest of this plan is written as if these decisions are made.
