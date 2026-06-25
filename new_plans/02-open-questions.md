# Open Questions

Genuinely undecided items that need your call — not things I'm hedging on, but real forks where your preference or constraints determine the answer. Resolve these before or during the relevant phase.

## Architecture / scope

**Q1 — Default mode at all, or air-gapped only?**
The whole "let Claude plan from a redacted bundle" path adds the egress gate, redaction rigor, and approval UI. If your footage is *always* too sensitive to send even a redacted bundle, you could build air-gapped-only and skip that machinery — simpler, but you lose frontier planning quality. My read: build air-gapped first (phase 4), add default mode only if local planning quality disappoints. **Your call: is there any project where a redacted, PII-masked, low-res bundle is acceptable to send?**

**Q2 — How much of the security spine at MVP?**
The proposer/compiler split is cheap and I'd keep it from phase 0 (it's also good for reproducibility). But full trust-domain *runtime* isolation (rootless containers, network namespaces, recorder service account) is phase-6 work. For your *own* footage on your *own* box, is the logical separation (proposer/compiler + local-only) enough to start, with runtime isolation deferred? My recommendation: yes, MVP with logical separation, harden later. **Confirm you're comfortable running phases 3–5 without full container isolation.**

**Q3 — 8GB or 16GB on the 4060 Ti?**
This changes the scheduling story materially. 8GB = serialize VLM and WhisperX; 16GB = co-resident, simpler queue. If you have (or can get) the 16GB card, the inference topology relaxes. **Which 4060 Ti do you have?**

## Capture

**Q4 — OBS or fork Cap's recorder?**
OBS is faster to integrate (obs-websocket) but clock sync across two processes (OBS + evdev broker) is the risk. Cap's single-process cursor-layer model is cleaner but a bigger build. Start with OBS; fork Cap only if R-class sync tests fail. **Agree to start with OBS, or do you want the cleaner Cap fork up front given you care about getting the zoom timing perfect?**

**Q5 — Rust broker now or Python first?**
Python `evdev` is faster to prototype; Rust is the hardened endpoint. Given you build pixel-art games in PixiJS and have a Rust/wgpu project (FastView), Rust isn't a barrier for you. **Prototype in Python and rewrite, or go straight to Rust for the broker?** (For a security boundary you'll keep, straight-to-Rust may be worth it.)

## Render

**Q6 — How hard to chase Screen-Studio parity?**
The aesthetic preset table (`03-components/05`) gets you close, but "indistinguishable" is iterative polish that can eat weeks. Is "clearly good, 90% there" enough for internal demos, or do you want pixel-parity? My read: 90% is plenty for internal use; don't sink weeks chasing the last 10% unless these demos are external-facing. **What's the actual audience for the output?**

**Q7 — Remotion dependency acceptable?**
It pulls in Node + headless Chromium — a heavy dependency and the largest attack surface in the stack. The MIT alternatives (Motion Canvas, Revideo) avoid the licensing question but are less mature. For a solo tool, Remotion's free tier covers you. **Comfortable with the Chromium dependency, or do you want to evaluate Motion Canvas to keep the stack lighter/MIT?**

## Verification

**Q8 — How much corpus before building forward?**
Minimum MVP corpus is C1/C4/C7 (edits/redaction/injection). Full corpus is 15 clips. Building the corpus is itself a weekend. **Build the 3-clip minimum and grow it from bugs, or invest in the full corpus up front?** (I'd do the minimum and grow it — corpora built from real failures are better than imagined ones.)

## Meta

**Q9 — Is this even worth building vs. just using Screen Studio on a Mac?**
The honest devil's-advocate question. If you had a Mac, Screen Studio is local, offline, on-device-transcription, and nails the aesthetic for $108/yr — the privacy argument mostly evaporates against *it specifically*. ClipMind wins on: Linux (you're on Linux), reproducibility/diffable edits, agent-driving, CI integration, zero cost, and air-gapped guarantee for the most sensitive footage. **Be honest with yourself: is the driver "I'm on Linux and want this," "I want reproducible/scriptable edits," or "I want to build it"? All three are valid, but they imply different stopping points.** If it's mostly "I want to build it," that's fine — just don't over-invest in hardening you'll never need. If it's "reproducible edits for regulated demos," the full plan earns its keep.

**Q10 — Single-user forever, or possible team use later?**
Several scope-trims (no authz, no RTO/RPO, solo incident checklist) assume single-user. If there's any chance a teammate uses this, the trust-domain architecture already supports it but the trimmed operational pieces would need to come back. **Plan for solo, or keep team-readiness in mind?**

---

## My default recommendations if you don't want to decide each

If you just want to start: 16GB card if you have it (Q3); MVP with logical separation, defer container isolation (Q2); air-gapped first, add default mode if needed (Q1); OBS + Python evdev broker to prototype, rewrite the broker in Rust once it works (Q4/Q5); 3-clip corpus grown from bugs (Q8); 90% aesthetic parity (Q6); accept Remotion (Q7). That path gets you a working, safe-enough, local tool in ~4–6 weekends, and you harden the parts that prove to matter.
