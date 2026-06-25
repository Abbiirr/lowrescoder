# PLAN_02 — The "Video Editing Agent" Brief

> A technical brief for a general-purpose, agentic, AI-capable video editing product. This is plan 2 of 3. Plan 1 (`ClipMind` in `README.md`) is a screen-recording-only tool with a 5-trust-domain architecture, FFmpeg + Remotion dual backend, and a Screen-Studio aesthetic. **This plan is for editing any user-supplied video — interviews, vlogs, lectures, talking heads, b-roll, livestream VODs, sports footage, music — not just screen recordings, and it must be a proper user-facing agent, not a CLI-in-a-loop.**

The brief is structured as: landscape → representation → perception → render → proposer/compiler pattern → local vs cloud → UX → differentiation. Each section ends with "**Where ClipMind already covers it**" / "**Where this plan diverges**" so the two plans compose rather than duplicate.

---

## 1. The video agent landscape (mid-2026)

### 1.1 Feature inventory

| Product | Core job | AI capability split | Where it fails |
|---|---|---|---|
| **Descript** ([descript.com](https://www.descript.com/)) | Transcript-as-timeline video editor | ASR-first, "Underlord" agent, AI speech (voice clone), AI B-roll, AI eye contact, filler-word removal | AI credits are a metered choke; long-form (>1hr) is expensive; export times are slow for 4K; agent is *chat-against-video*, not a long-running multi-step editor |
| **Runway** ([runwayml.com](https://runwayml.com/)) | Generative video platform (Gen-4.5) + VFX | Heavy on generation; Aleph/Act-Two for VFX on existing footage; GWM-1 world model | Generation cost dominates; not optimized for "edit the video I already have"; clip length caps at ~10s for generation |
| **Pika** ([pika.art](https://pika.art/)) | "Idea-to-video" with Pikaffects (Squish/Melt/Cake-ify) | Pika 2.5 generative model + Pikaswaps + **Pika Agent** + **Pika MCP** server | Mostly transformative (one-tap effects) rather than structural editing; the agent is brand-new and narrow |
| **Opus Clip / Opus Pro** ([opus.pro](https://www.opus.pro/)) | Long-video → short-clips repurposing | ClipAnything (highlight detection), ReframeAnything (auto-reframe with subject tracking), 97% captions, brand templates | One-shot pipeline (you give it a long video, get 10 clips); not a general editor; no timeline; no re-edit of a clip beyond captions |
| **CapCut** ([capcut.com](https://www.capcut.com/)) | Free mobile/desktop editor with AI templates | Auto-captions, TTS, BG removal, "Dreamina" generative model, "Pippit" creative agent | Auto-cuts are template-driven, not intentional; export limits on free tier; agent features are still in early roll-out |
| **Captions** ([captions.ai](https://www.captions.ai/)) | "AI that edits like a professional editor" | Prompt-driven editing, AI actors, AI dubbing, image-to-video | Tends toward generation rather than structural edit; black-box pipeline; no transparency on what it did |
| **VEED** ([veed.io](https://www.veed.io/)) | Browser-based Swiss-army-knife | Model-agnostic playground (Sora 2, VEO 3, Kling O1, etc.), Magic Cut, AI dub, AI avatar | A *marketplace of models* rather than a coherent editor; expensive; web-only at edit time |
| **Screen Studio** ([screen.studio](https://screen.studio/)) | macOS screen recorder with cursor zoom, smoothing, BG | Effectively zero AI; deterministic cursor-aware effects | Mac-only; no agent; no editing of arbitrary footage |
| **AutoCut / TimeBolt / Descript filler-removal** | Silence/jump-cut detection → edit | Heuristic, deterministic; some use Whisper under the hood | One-trick-pony; no full NLE; no agentic orchestration |
| **Open source: Serge, Video_Editor_MCP, vfx-mcp** | LLM chat frontends or MCP tool surfaces for video | None of these are full agents. Serge is a llama.cpp chat UI. Video_Editor_MCP is a tool surface; you bring the agent. | No product; you must wire the agent yourself |

### 1.2 The capability split

Three distinct AI jobs that get conflated in marketing:

1. **Text-to-video / image-to-video** — generative models (Sora 2, VEO 3, Runway Gen-4.5, Pika 2.5, Kling O1). These create pixels. They are *not* this plan. The plan edits existing pixels.
2. **Video-editing-assistant** — chat-with-video where the LLM suggests a cut, you accept. Descript Underlord, Pika Agent, Captions' prompt box. Single-turn or short-loop, not multi-step.
3. **Video understanding** — perception (ASR, scene detection, object detection, OCR). Building block for any agent. The LLM never sees raw pixels in our model — it sees structured text.

### 1.3 The gap

The market has lots of **(2)** — single-prompt assistants — and lots of **(1)**. The genuinely empty slot is **autonomous, multi-step, long-running editing agents that operate on user-supplied video, return a finished cut, and are auditable/deterministic under the hood.** Opus Clip is the closest (it does multi-step highlight → reframe → caption → publish in one go) but it's a narrow pipeline, not a general editor.

**The opportunity is a Descript-shaped product where the chat surface becomes the *primary* UI and the timeline is a result, not the workspace.**

### 1.4 Where ClipMind already covers it / diverges

**ClipMind covers:** perception pipeline, FFmpeg + Remotion dual backend, proposer/compiler split, content-addressed artifact store, low-level editing operations.
**This plan diverges:** broader input (any video, not just screen recordings), agentic UI as the *primary* interaction, no Screen-Studio aesthetic (no synthetic cursor, no zoom-on-click — those are screen-recording idioms), no evdev capture domain (the user is supplying footage, not recording it), and a more general perceptual schema (faces, music, actions, not just text and clicks).

---

## 2. Agentic editing patterns — how to represent edit state

### 2.1 The options

| Representation | Strengths | Weaknesses for an agent |
|---|---|---|
| **CMX 3600 EDL** | 40-year standard, line-based, human-readable | One event per cut; transitions/effects are limited; no metadata |
| **Final Cut Pro XML / Premiere XML** | Industry standard, rich | Verbose, vendor-specific quirks, hard for an LLM to author |
| **OpenTimelineIO (OTIO)** | Open, well-typed, multi-vendor, in-memory edit of tracks/clips/gaps/transitions/markers/effects | Heavier; less familiar to LLMs (more tokens); schema is rich enough that LLMs get nesting wrong |
| **JSON EDL (custom)** | Compact, JSON-Schema validatable, easy to author and diff, easy to lint | You write the compiler |
| **Render DAG (FFmpeg filtergraph)** | Compiled, directly executable, deterministic | Unreadable; not editable by hand; not what the LLM should author |
| **Lua/Python DSL** | Powerful, expressive | LLMs are bad at code that *isn't* type-checked at edit time |

### 2.2 The agent-friendly choice

**Typed JSON Edit Decision List → compiler → render DAG.** This is the same pattern ClipMind uses, and the same one the CaMeL / proposer-compiler literature supports. The agent authors a *declarative* Change Request; the compiler is a non-LLM deterministic validator + code generator that emits either an FFmpeg `filter_complex` or a Remotion composition.

The Change Request schema should support at minimum:

```jsonc
{
  "version": "1.0",
  "intent": "polish_lecture_for_youtube",
  "project_hash": "sha256:...",
  "ops": [
    { "op": "cut",       "source_in": "00:01:12.40", "source_out": "00:01:58.10" },
    { "op": "trim",      "clip_id": "c1", "in": 0.4, "out": 12.0 },
    { "op": "crop",      "clip_id": "c1", "box": { "x": 240, "y": 0, "w": 1440, "h": 1080 } },
    { "op": "zoom",      "clip_id": "c1", "scale": 1.5, "anchor": "face", "t": 2.0, "duration": 1.5 },
    { "op": "speed",     "clip_id": "c1", "rate": 1.2 },
    { "op": "caption",   "clip_id": "c1", "text": "...", "style": "word-by-word", "words": [{ "t": 0.0, "w": "Hello" }] },
    { "op": "callout",   "clip_id": "c1", "shape": "circle", "target": "evidence:face:42" },
    { "op": "color",     "clip_id": "c1", "lut": "warm_indoor" },
    { "op": "transition","from": "c1", "to": "c2", "type": "xfade", "duration": 0.4 },
    { "op": "broll",     "in": "00:01:30.00", "out": "00:01:34.00", "query": "aerial city skyline" },
    { "op": "music_duck","track": "music", "below": "voice", "ratio_db": -12 },
    { "op": "overlay",   "clip_id": "c1", "layer": "logo", "position": "tr", "opacity": 0.7 }
  ]
}
```

The **op grammar is the agent's API surface** — small, closed, fully typed. LLMs are good at emitting JSON; they're bad at authoring 2000-line filtergraphs.

### 2.3 Why not OTIO as the agent's native format?

OTIO is the *right compiler target* (the DAG level). The LLM authoring layer should be a thin JSON DSL that the compiler expands to OTIO (or directly to filter_complex / Remotion). This is the same insight as CaMeL: keep the LLM near *proposals*, not the *execution graph*.

### 2.4 Where ClipMind already covers it / diverges

**ClipMind covers:** the typed Change Request + Execution DAG split, the schema, the validation rules, the FFmpeg/Remotion dual backend.
**This plan diverges:** broader op vocabulary (b-roll, music ducking, transitions, color LUTs, multiple audio tracks), intent field at the top of the CR (so multi-step plans can be tracked), and a layer of *named intent templates* (e.g. `polish_lecture_for_youtube`, `clip_highlights_for_tiktok`, `make_me_a_trailer`) that the agent picks from — these templates are themselves pre-validated CR skeletons.

---

## 3. Perception pipeline for general video — the "Evidence Manifest"

ClipMind's perception is screen-recording-shaped: transcript, OCR, click events, cursor positions. General video needs more: who is on screen, what they're saying, what's happening, where the music is, where the silences are, what the text on screen says.

### 3.1 The Evidence Manifest (expanded)

```jsonc
{
  "project_hash": "sha256:...",
  "duration_s": 7242.3,
  "tracks": {
    "video": [{ "stream": 0, "codec": "h264", "w": 1920, "h": 1080, "fps": 30 }],
    "audio": [{ "stream": 1, "codec": "aac", "sr": 48000, "ch": 2 }]
  },
  "scenes":       [ { "id": "s0", "start": 0.0,    "end": 12.4,  "method": "pyscenedetect.content" } ],
  "shots":        [ { "id": "sh0", "start": 0.0,  "end": 4.2,   "type": "wide" } ],
  "transcript":   [ { "speaker": "S1", "start": 0.2, "end": 4.1, "text": "...", "words": [...], "lang": "en" } ],
  "faces":        [ { "id": "face:42", "track": "t0", "start": 12.0, "end": 58.0, "embedding": "vec:..." } ],
  "objects":      [ { "label": "car",  "track": "t1", "start": 22.0, "end": 25.0, "box": {...} } ],
  "on_screen_text":[ { "text": "Q3 revenue +12%", "t": 245.0, "duration": 4.2, "box": {...} } ],
  "music":        [ { "start": 0.0,  "end": 120.0, "type": "score", "bpm_est": 96 } ],
  "silences":     [ { "start": 31.0, "end": 33.2 } ],
  "sound_events": [ { "start": 18.0, "end": 19.0, "label": "applause" } ],
  "actions":      [ { "start": 100.0, "end": 105.0, "label": "person_dances" } ],
  "keyframes":    [ { "t": 1.0, "thumb_hash": "sha256:..." } ]
}
```

### 3.2 The building blocks

| Layer | Open-source tool | Notes |
|---|---|---|
| **Scene detection** | [PySceneDetect](https://www.scenedetect.com/) (ContentDetector, ThresholdDetector, AdaptiveDetector) | Tune `threshold` and `min_scene_len`; second pass with TransNetV2 for shotty content |
| **Shot boundary** | TransNetV2 | Deep-learning cut detector; better than PySceneDetect on fast cuts/gradual transitions |
| **Speech recognition** | [WhisperX](https://github.com/m-bain/whisperX) on top of faster-whisper; whisper.cpp for fully-local | Word-level timestamps via wav2vec2 forced alignment; 70× realtime on large-v2 with <8 GB VRAM |
| **Speaker diarization** | pyannote-audio (`pyannote/speaker-diarization-community-1`) | Pairs with WhisperX output |
| **Face detection + embedding** | InsightFace (RetinaFace + ArcFace) | Track a face across shots; cluster to "person:0", "person:1" |
| **Object detection** | GroundingDINO + SAM2 (open-vocabulary) or YOLOv10 (closed vocabulary) | Open-vocab is essential for "find me a shot with a coffee cup" |
| **On-screen text** | PaddleOCR (PP-OCRv4) | Tesseract 5 is fine for English but Paddle is faster + multilingual |
| **Music / music-type detection** | CREMA, AudioSet YAMNet, Essentia | Distinguish score vs speech vs ambience |
| **Silence / audio events** | ffmpeg `silencedetect`, PANNs, BEATs | Cheap on CPU; PANNs for event classes |
| **Action recognition** | VideoMAE, InternVideo, SlowFast | Heavy — only enable when explicitly asked |
| **Keyframe sampling** | ffmpeg select=expr (inter-frame diff), or PyAV with a thumbnail budget | E.g. 1 keyframe per 4 s is usually enough for an agent's mental model |
| **VLM caption (optional)** | Qwen2.5-VL 7B (Q4), LLaVA-OneVision | Quarantined — used for *evidence description* only, never the planner |

### 3.3 What the planner actually gets

A **text-first, low-resolution, evidence-hash-referenced Bundle** — never raw pixels. The planner sees something like:

```
Project: interview-jane-doe.mov  (sha256:a1b2…)
Duration: 1h 12m 04s

Speakers: S1 (woman, 32 min total), S2 (man, 41 min total)
Scenes: 47 cuts, mean shot length 1.5s (range 0.4–18.0s)
On-camera text: 14 title cards detected (samples: ...)

S1 [00:00:12–00:00:48]: "I think the real insight is that the model is overfitting to the eval, not to the problem."
  -> ref evidence:face:42, evidence:word:0:00:12:30

S2 [00:00:50–00:01:12]: (interrupts, "Right, but the eval *is* the problem because...")
  -> ref evidence:face:43, contains laughter at 00:01:08

Music: scored intro 0:00–0:18 (upbeat, 96 bpm)
       scored outro 1:10:42–1:12:04 (soft)
       otherwise clean dialogue
Silences: 23 (>2.0s)
```

The LLM reasons over this. It can request more — *"sample 5 frames around 0:45:00"* — but it never gets the raw stream.

### 3.4 Where ClipMind already covers it / diverges

**ClipMind covers:** PySceneDetect, WhisperX, OCR, silencedetect, contact sheets; the cheap-perception design; the Evidence Bundle as planner input.
**This plan diverges:** adds faces (InsightFace), objects (GroundingDINO), music detection (CREMA/AudioSet), on-screen text as first-class, scene *type* classification (interview/wide/b-roll), and a per-feature budget so the perception pass is configurable (e.g. "skip face detection for a landscape timelapse").

---

## 4. Render engine options

| Engine | Control | Determinism | Perf | Learning curve | Best for |
|---|---|---|---|---|---|
| **FFmpeg filtergraph** | Total | Perfect (pinned codecs, `-smpf`, `timebase`) | Fastest (native, no extra layer) | Steep (filter syntax) | All structural edits: trim, concat, xfade, drawtext, overlay, color |
| **Remotion** ([remotion.dev](https://www.remotion.dev/)) | High (React) | Good (frame-accurate) | Slow (Chromium, ~5–10× real-time for complex comps) | Moderate (React + TS) | Motion graphics: animated captions, zooms, callouts, intros |
| **Motion Canvas** | High (TS) | Good | Moderate | Moderate | Similar to Remotion, MIT-licensed, lighter weight |
| **Revideo** | High (TS, After Effects-like) | Good | Moderate | Moderate | Programmatic video with AE-style animation curves |
| **MLT framework** | High (XML + melt CLI) | Good | Fast | Steep | Multi-track timelines; less popular now |
| **GStreamer** | Total | Perfect | Fastest on supported HW | Steepest | Realtime pipelines, low-level control |
| **OpenCV-based** | Pixel-level | Good | Slow (Python) | Low | Compositing, face FX, custom effects |
| **Puppeteer/headless Chromium** | High (CSS/HTML/JS) | Imperfect (font metrics, rendering drift) | Slow | Low | Text-heavy motion graphics; captions |

### 4.1 Recommendation

**Two backends, same as ClipMind:** FFmpeg for the structural skeleton (99% of the work — trim, cut, concat, xfade, color, captions-as-bitmap, audio duck), and Remotion only for the 1% that needs motion graphics (animated captions, spring zooms, callout animations). This avoids pulling in Chromium for the common case and keeps the render path fully deterministic.

**Important divergence from ClipMind:** don't let Remotion own the *primary* render. For a general video editor, FFmpeg-only is the right default; Remotion is a *progressive enhancement* for users who opt in to motion graphics. In ClipMind, Remotion is needed for the Screen-Studio aesthetic; here, that's an effect pack, not a backend.

### 4.2 Where ClipMind already covers it / diverges

**ClipMind covers:** FFmpeg + Remotion dual backend, deterministic encoder pinning, the DAG-of-render-nodes model.
**This plan diverges:** defaults to FFmpeg-only for MVP; Remotion is opt-in for "polished" presets. Different release targets mean a different backend selection algorithm.

---

## 5. "Agent proposes, compiler authorizes" — the Change Request pattern

This is the core architectural pattern and it generalizes straight from ClipMind. The agent is a *proposer* that emits typed Change Requests. The compiler is a *non-LLM* deterministic validator that:

1. Parses the CR.
2. Verifies the JSON Schema.
3. Verifies invariants:
   - `source_in < source_out`; `in < out`; `out <= duration`.
   - `clip_id` references exist.
   - `from`/`to` references are valid pairs.
   - `broll` queries reference indexed evidence or a stock library.
   - No `op` of a type not in the allowed list.
   - Sensitivity label on the CR is ≤ the source's label.
   - No `shell`, `path`, `command` fields in the CR (schema rejects).
4. Compiles to a render DAG (FFmpeg filtergraph or Remotion props + JSX).
5. Emits a preview render and waits for user approval.

### 5.1 The CR's op vocabulary (for a general video editor)

Already listed in §2.2. To call out the additions that screen-recording editors don't need:

- `broll` — insert stock/AI-generated footage over a span.
- `music_duck` — duck one audio track under another.
- `transition` — xfade / dissolve / wipe / dip-to-color.
- `color` — LUT, white balance, exposure.
- `pan` — pan/zoom inside a frame (Ken Burns, follow-face).
- `overlay` — graphic / logo / lower-third.
- `normalize_audio` — loudness normalize to a target LUFS.
- `jcut` / `lcut` — audio leads or trails the cut.
- `chapter` — write chapter markers (YouTube, podcast).

### 5.2 Multi-step plans

A long-running editing task is a **list of CRs**, not one. The agent proposes *step 1*, the compiler validates and previews, the user approves (or the agent's own stop condition approves), then the agent proposes *step 2*, etc. The agent's state machine is:

```
[perceive] → [propose CR_n] → [validate] → [preview] → [approve]
                                ↑                       ↓
                                └───[rejected]←──────────┘
```

Each step is independently replayable, and every CR is content-addressed (`sha256`) so the whole plan is auditable, diffable, and resumable.

### 5.3 Named intent templates (the "agent's starter moves")

These are pre-validated, well-tested CR skeletons the agent can choose from:

- `polish_lecture_for_youtube` — remove silences, dead air, "ums"; add intro/outro; burn captions; add chapter markers; normalize audio to -16 LUFS; 1080p, 30 fps.
- `clip_highlights_for_shorts` — find 5–10 best 60-s segments (semantic + acoustic scoring), reframe 9:16 with face tracking, add captions, end with CTA.
- `make_me_a_trailer` — score energy curve, pick 8–12 high-energy shots, cross-cut on beat, add titles, 60s output.
- `interview_to_article` — full transcript, speaker turns, quotes, formatted Markdown.
- `screen_recording_polish` — ClipMind's preset, included for completeness.
- `livestream_vod_to_chapters` — chapterize, remove waiting-room, fix audio levels.

### 5.4 Where ClipMind already covers it / diverges

**ClipMind covers:** the proposer/compiler split, the schema, the validation rules, the dual-trust LLM pattern.
**This plan diverges:** broader op vocabulary, intent templates as a user-facing concept, the multi-step plan as a first-class object, and a *different* agent-runtime contract — this plan's agent runs in a managed loop (not Claude Code's PreToolUse/Stop hook model), so the compiler is exposed as a typed API to whatever LLM runtime we choose (Claude, GPT-4o, local Qwen2.5-VL, etc.).

---

## 6. Local vs cloud tradeoffs

| Factor | Local-only | Cloud-only | Hybrid (recommended) |
|---|---|---|---|
| **Privacy** | Best (raw never leaves) | Worst (must trust vendor) | Good (perception local; planning on redacted bundle) |
| **Latency** | Best for cached assets; depends on GPU for cold | Predictable, no GPU needed | Mixed: perception local, planning round-trip |
| **Cost** | Upfront hardware; zero marginal | Pay-per-minute; agent runs add up | Mostly local; cloud only for planning tokens |
| **Model capability** | 8B-class VLMs are good, not frontier | Frontier models available | Best of both (Qwen2.5-VL local + GPT-4o/Claude for planning) |
| **Offline** | Works | Doesn't | Mostly works |

### 6.1 The recommended split

- **Local (always):** FFmpeg, PySceneDetect, WhisperX (faster-whisper), InsightFace, PaddleOCR, YAMNet, silencedetect, Qwen2.5-VL-7B-Instruct-Q4 for perception *descriptions only*.
- **Cloud (opt-in):** Claude / GPT-4o for the planning step over the redacted Bundle.
- **Local (always):** the render (FFmpeg/Remotion).

This is essentially the same hybrid ClipMind describes, but generalized: there is no capture domain, so the perimeter is just "what runs on your box."

### 6.2 A fully-local path

For the privacy-maximalist or air-gapped case, a fully-local stack is viable on a single 16 GB GPU (or 8 GB with serialized stages):

- Qwen2.5-VL-7B-Instruct (Q4) as the planner.
- WhisperX large-v3 (faster-whisper, int8) for ASR.
- InsightFace + buffalo_l for faces.
- PaddleOCR for text.
- FFmpeg for render.

This produces noticeably worse planning than Claude/GPT-4o for tricky tasks (e.g. "find the moment the speaker contradicts themselves") but is excellent for structural edits (cut, trim, caption, remove silence). The MVP should default to cloud-planning; the local path is a toggle.

### 6.3 Where ClipMind already covers it / diverges

**ClipMind covers:** the local-VLM-on-the-4060-Ti topology, the egress gate, the redaction pass.
**This plan diverges:** no capture domain to isolate, so the egress gate is simpler (just: "are we sending the Bundle to a model?"). The local-VLM hardware target is the same class but the *use* is different: ClipMind uses Qwen3-VL-8B for *captions of frames* (zoomed cursor screenshots); this plan uses Qwen2.5-VL-7B for *general scene understanding*.

---

## 7. UX patterns — what works for an agentic editor

Four dominant UX shapes in 2026:

1. **Timeline-first** (Premiere, Resolve, Final Cut). Mature, powerful, opaque to AI. Bad fit for an agent — the LLM would have to read a complex visual UI.
2. **Script-first** (Descript). Edit the transcript; the timeline reflects it. Works for talking-head video. Doesn't scale to b-roll, music, VFX.
3. **Storyboard-first** (CapCut, TikTok editor). Cards in a vertical strip. Mobile-friendly, low ceiling.
4. **Text-prompt-first** (Runway, Captions, Pika). "Make it cinematic." Black-box, generative, single-shot.

### 7.1 What an agentic editor needs

A **conversation-with-the-video** UI where the *primary* surface is a chat with the rendered artifact, and the *secondary* surface is a timeline that the agent drives. The user types intent; the agent proposes; the user reviews the diff (a side-by-side of the CR applied to the source); the user approves.

Sketch:

```
┌──────────────────────────────┬────────────────────────────────────┐
│  video preview               │  agent                            │
│  ┌────────────────────────┐  │  ┌──────────────────────────────┐  │
│  │                        │  │  │ user: tighten this lecture   │  │
│  │       [playhead]       │  │  │ agent: removed 3m14s of      │  │
│  │                        │  │  │   silence, burned 4 caption  │  │
│  │                        │  │  │   blocks, normalized to      │  │
│  └────────────────────────┘  │  │   -16 LUFS. preview ready.   │  │
│  ◀━━●━━━━━━━━━━━━━━━━━▶ 1:12 │  │                              │  │
│                              │  │ user: also add chapter marks │  │
│  changes (CR diff)           │  │ agent: 5 chapters, 1:00:00   │  │
│   ✂️ 00:12:40 – 00:14:10     │  │   apart.                      │  │
│   ✂️ 00:31:00 – 00:34:14     │  │                              │  │
│   📝 captions burned         │  │ user: 8:00 apart              │  │
│   🔊 normalized              │  │ agent: done.                  │  │
│                              │  │                              │  │
│  [reject] [preview] [accept] │  │ [retry] [apply]               │  │
└──────────────────────────────┴────────────────────────────────────┘
```

### 7.2 The "multi-step agent loop" UI

For long tasks (e.g. "watch this 2-hour interview, pull 5 best 60-second clips, overlay captions, brand them"), the UI needs:

- A **plan panel** showing the steps and their state.
- A **live preview** for the current step's output.
- A **side-by-side diff** at the end.
- An **audit log** of every CR the agent emitted and what the compiler accepted/rejected.

This is closer to a coding agent's UI (Claude Code, Cursor) than a video editor. That's intentional: video editing is becoming a *code-shaped* task — many small, typed, replayable operations on a large artifact.

### 7.3 Where ClipMind already covers it / diverges

**ClipMind covers:** Claude Code as the harness, SKILL.md, hooks, the propose/compile/render loop.
**This plan diverges:** the user-facing UI is the product, not Claude Code. Claude Code is one of several runnable backends; the product is a web/desktop app with a chat surface, a preview, and a CR diff. The agent runtime is pluggable (Claude, GPT-4o, local Qwen2.5-VL, a LangGraph loop, a custom controller) — they all speak the same CR JSON.

---

## 8. Differentiation — the agent-native angle

A new entrant in 2026 has to be more than a "Descript clone with one extra feature." The agent-native differentiators:

### 8.1 The user-facing "edit-by-intent" promise

The product line is described as verbs, not nouns:
- **"Edit this lecture into a YouTube video."** (Polishing)
- **"Pull 5 best 60-second clips from this 2-hour interview."** (Highlight extraction)
- **"Make me a 30-second trailer."** (Synthesis)
- **"Turn this VOD into a podcast."** (Re-purposing)
- **"Remove the silences, add captions, brand it."** (Tactical)

Each of these is a *named intent template* (§5.3). The agent picks the template, fills the slots, and emits a CR.

### 8.2 The technical differentiators

1. **Auditable CR history.** Every edit is a JSON object in git, content-addressed, replayable. Descript's edit history is opaque; this is diffable.
2. **Deterministic re-render.** Pin encoder settings, timebases, and codec params. Re-render is byte-identical for the same CR + source.
3. **Pluggable agent runtime.** Use Claude, GPT-4o, local Qwen, or your own — they all speak CR.
4. **Open CR schema.** The schema is published; the compiler is open source. Users can write their own templates.
5. **Multi-track awareness.** Music, voice, SFX, ambience as first-class tracks with ducking/sidechain as typed ops. Descript treats audio as monolithic.
6. **Local-first option.** Run fully air-gapped; ClipMind-style trust-domain isolation is overkill, but a "no network egress ever" mode is table-stakes for some users.
7. **Multi-step plan UI.** A real plan panel, not a single prompt. Closest analog is Devin / Claude Code for code; nothing equivalent for video.

### 8.3 The honest limits

The plan does *not* match Descript on:
- Built-in AI speech (voice clone) and AI B-roll generation. Generative models are a separate stack; the MVP doesn't ship them.
- Cross-user collaboration. Solo-first; team later.
- Mobile. Desktop + web only at MVP.

The plan does match Descript on:
- Transcript-driven editing (where the source is talking-head).
- Auto-captions.
- Filler-word removal.
- Multi-track audio (better, in fact).

The plan *exceeds* Descript on:
- Multi-step autonomous plans.
- Auditable / replayable / diffable edits.
- Local-first.
- Pluggable model.

### 8.4 Where ClipMind already covers it / diverges

**ClipMind covers:** the proposer/compiler split, the typed CR, the local-first principle, the FFmpeg + Remotion backend.
**This plan diverges:** *not* a screen-recording tool, *not* a one-engineer-internal tool, *not* a CLI loop. It is a product with a UI, a multi-step plan model, a pluggable agent runtime, and a broader perceptual schema. Where ClipMind's value is "I can edit my own screen recordings without trusting a cloud vendor," this plan's value is "I can hand a video to an agent and trust that the result is what I asked for, with a paper trail."

---

## Appendix A — Sources

- [Descript](https://www.descript.com/) — Underlord AI agent, AI credits, transcript-first editing.
- [Runway](https://runwayml.com/) — Gen-4.5, Aleph, Act-Two, GWM-1 world model.
- [Pika](https://pika.art/) — Pika 2.5, Pikaffects, Pika Agent, Pika MCP server.
- [Opus Clip](https://www.opus.pro/) — ClipAnything, ReframeAnything, 26+ languages, viral-clip pipeline.
- [CapCut](https://www.capcut.com/) — CapCut + Dreamina + Pippit; mobile-first AI editor.
- [Captions](https://www.captions.ai/) — "AI that edits like a professional editor," prompt-driven, AI actors, dubbing.
- [VEED](https://www.veed.io/) — Model-agnostic AI playground (Sora 2, VEO 3, Kling O1), Magic Cut, browser-based.
- [Screen Studio](https://screen.studio/) — macOS screen recorder, cursor zoom/smoothing, no AI.
- [Remotion](https://www.remotion.dev/) — React-based programmatic video, MP4 output, $0.01/render.
- [FFmpeg](https://ffmpeg.org/documentation.html) — `filter_complex` syntax, trim/concat/scale/crop/overlay/drawtext/xfade/atemp/setpts.
- [PySceneDetect](https://www.scenedetect.com/) — ContentDetector, ThresholdDetector, AdaptiveDetector.
- [WhisperX](https://github.com/m-bain/whisperX) — 70× realtime, word-level alignment via wav2vec2, pyannote diarization.
- [LangChain](https://www.langchain.com/) — LangGraph (deterministic agents), deepagents (long-running), tracing/eval/HITL.
- [Serge](https://github.com/serge-chat/serge) — (For reference: it's a llama.cpp chat UI, not a video editor. Not the right reference for an editing agent.)

## Appendix B — Where this plan composes with ClipMind

| Concern | ClipMind | This plan |
|---|---|---|
| Trust-domain architecture | Five domains, recorder isolated | Three: Perception, Planning, Render. No Capture. |
| Proposer/compiler split | Yes (inherited from CaMeL) | Yes (same) |
| Content-addressed artifacts | Yes | Yes |
| Deny-by-default egress | Yes | Yes (simpler — no capture domain) |
| FFmpeg + Remotion dual backend | Yes (Remotion owns aesthetic) | Yes (Remotion is opt-in) |
| Local VLM | Qwen3-VL-8B for cursor screenshots | Qwen2.5-VL-7B for general scenes |
| CR schema | Screen-recording ops | General video ops (b-roll, music, transitions) |
| Multi-step plan model | Implicit (Claude Code loop) | Explicit (named intent templates, plan panel) |
| UI | Claude Code SKILL.md | Web/desktop product with chat + preview + diff |
| Audience | Solo engineer, internal demos | General user, product |
