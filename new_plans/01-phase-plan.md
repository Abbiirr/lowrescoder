# Phase Plan

Phases 0–6 with effort, exit criteria, and build-vs-fork per phase. Two endpoints are marked: the **MVP** (a useful, reasonably-safe tool — a few weekends) and the **hardened** version (the adversarial review's 16–24 week target). You choose where to stop.

The sequencing rule from the review, which I agree with: **build the recorder boundary first (hardest to retrofit), the compiler second (determines whether the system stays safe or drifts into shell-agentics), and delay the external-model path until redaction + approval + audit work.**

---

## Phase 0 — Render core + spec (no AI)
**Goal:** prove the deterministic spine works before any intelligence.
- Define the three-layer schema (Manifest / Change Request / Execution DAG) — start with Change Request + a minimal Manifest.
- Implement the compiler: validate a Change Request → compile to Execution DAG.
- Implement `render_spec` over FFmpeg for trim/concat/speed/crop/caption-burn.
- Pin deterministic encoder settings. Commit Change Requests to git.

**Build:** schema, compiler, FFmpeg renderer. **Fork/use:** FFmpeg, ffmpeg-python.
**Exit:** hand-write a Change Request, get a clean cut demo out, re-run → identical decisions.
**Effort:** ~1 weekend.

## Phase 1 — Perception tools
**Goal:** turn footage into a cheap text bundle.
- Wire PySceneDetect + WhisperX + ffmpeg contact-sheet + silencedetect + PaddleOCR into one `perceive()`.
- Produce the Evidence Manifest. Validate VRAM/time on a real 2-min demo.

**Build:** the bundler + Manifest writer. **Fork/use:** PySceneDetect, WhisperX, auto-editor, PaddleOCR.
**Exit:** `perceive()` returns a bundle a model could plan from; total time < 1 min, all local.
**Effort:** ~1 weekend.

## Phase 2 — evdev capture + recorder (DO THIS EARLY)
**Goal:** trustworthy, time-aligned cursor/click stream. **The riskiest phase — hardest to retrofit.**
- Build the evdev broker (Python MVP): pointer-only filter, HMAC signing, narrow API.
- Integrate OBS (cursor off, composite synthetic later). Solve clock sync (shared `t0`).
- Validate: click at a known visual marker, confirm logged `t` matches the frame (drift < 2 frames).

**Build:** broker + launcher + sync. **Fork/study:** Cap's recorder.
**Exit:** a recording + a time-aligned, signed `events.jsonl`; zoom placement is frame-accurate.
**Effort:** ~1–2 weekends (sync bugs eat time — budget for it).

## Phase 3 — MCP server + Claude Code loop  ← **MVP endpoint**
**Goal:** the full perceive → propose → compile → render → verify loop.
- FastMCP server: `perceive`, `describe_frames`, `propose`, `sample_frames` (no shell).
- SKILL.md + references. PostToolUse git-commit + Stop validation hooks.
- The compiler's `propose` chokepoint: reject out-of-bounds, return explainable violations.
- Achieve: "tighten this demo, zoom on the clicks, add captions" → approved preview.

**Build:** MCP server, skill, hooks, the verify loop. **Fork/study:** vfx-mcp / Video_Editor_MCP for tool-surface shape only.
**Exit:** one natural-language request produces an approved 4K with auto-zoom + captions + dead-air removed, faster than doing it by hand.
**Effort:** ~1–2 weekends.

> **At the end of Phase 3 you have a working tool.** It already has the proposer/compiler split (so it's injection-resistant) and is local-only (so footage doesn't leave). It lacks the heavy hardening below. For your own footage, this is a reasonable place to live and iterate.

## Phase 4 — Local VLM perception
**Goal:** footage-derived perception 100% on-device.
- Stand up Qwen3-VL-8B (Q4) on the 4060 Ti via Ollama/gateway; wire `describe_frames` to it (quarantined prompt).
- Decide per-project local-vs-Claude planning (air-gapped vs default mode).
- Implement the egress gate at the gateway (deny-by-default; gated redacted path).

**Build:** quarantined VLM integration, egress gate, redaction pass.
**Exit:** in air-gapped mode, nothing footage-derived leaves; in default mode, only a redacted, approved Bundle does.
**Effort:** ~1 weekend (you already run local inference).

## Phase 5 — Aesthetic polish (Remotion)
**Goal:** output indistinguishable from Screen Studio.
- Second render backend: spring zoom, background/padding/shadow, synthetic cursor + smoothing + motion blur, animated captions, intros/outros.
- Change Request → Remotion props. Install Remotion's Claude Code skills.
- Tune the preset table on the golden corpus.

**Build:** Remotion compositions + compiler routing. **Fork/use:** Remotion (+ official skills).
**Exit:** side-by-side, your output matches Screen Studio on the core look.
**Effort:** ~2 weekends (motion graphics polish is iterative).

## Phase 6 — Hardening + headless/batch  ← **hardened endpoint**
**Goal:** the deployable, auditable version (the review's 16–24 week target, mostly here).
- Trust-domain isolation as real runtime boundaries: rootless containers, scoped GPU, `--network=none`, recorder service account.
- SBOM + signed builds + SLSA-ish provenance (only if regulated footage demands attestation).
- Headless FastAPI/LangChain loop reusing the MCP tools (CI: regenerate demos on release).
- OTIO export adapter for Resolve/Premiere handoff.
- The lightweight incident checklist; retention reaper; log hygiene.

**Build:** isolation, provenance, headless loop, OTIO adapter.
**Exit:** repeatable release; isolation verified by the security test suite; air-gapped mode provably leak-free.
**Effort:** weeks, not weekends — this is where the review's timeline lives.

---

## Effort summary

| Endpoint | Phases | Realistic effort | What you get |
|---|---|---|---|
| **MVP** | 0–3 | ~4–6 weekends | Working local tool, injection-resistant, FFmpeg render |
| **+ local VLM + polish** | 4–5 | +3 weekends | Fully on-device perception, Screen-Studio-grade output |
| **Hardened** | 6 | weeks | Container isolation, provenance, CI, audit — the review's endpoint |

## What changes the plan (decision triggers)

- Preview render > 15s → drop preview to 360p/15fps or render only changed DAG nodes.
- Local VLM perception > 30s/iteration → fewer keyframes, harder downscale, lean on transcript+OCR.
- An effect's FFmpeg filtergraph becomes unmaintainable → move it to Remotion.
- evdev clock drift > a few frames → single-process recorder (fork Cap).
- A project's sensitivity forbids any external call → air-gapped mode (already supported).
