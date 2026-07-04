"""Anvil — AutoCode's offline harness-evolution engine (PLAN_04 / PLAN_05).

Anvil is AutoCode's *build-time* self-improvement engine. It is **offline**: it
never touches the runtime, and only ever influences it through eval-gated,
operator-approved, reversible artifacts (an appended playbook delta, or a
promoted patch bundle). The runtime stays cloud-free and frozen-model.

Anvil has two legs:

* **Teacher mode (PLAN_04).** Turns failed/weaker AutoCode trajectories into
  reversible playbook deltas and prediction-contracted harness fixes. Runs
  ``puku-cli`` as the teacher and ``autocode`` as the student against the same
  executable oracle. *(Companion leg; built separately.)*

* **Copycat mode (PLAN_05) — implemented here.** Capability acquisition through
  three observable channels, all authorization-gated by the registry:

  - **Channel A — structural imitation** (:mod:`autocode.anvil.propose` et al.).
    Read the *public, observable* structure of a strong harness
    (``puku-cli``), diff it against AutoCode's own capability manifest, and
    draft *clean-room* capability proposals. It never vendors third-party
    source — structural imitation produces new AutoCode components evaluated on
    the oracle, never copied code.

  - **Channel B — outcome distillation** (:mod:`autocode.anvil.copycat`). Drive
    an authorized target, capture the verified final artifact (the diff), and
    either (a) use it as a weak eval-oracle (always safe; ``reuse_scope:
    outcomes``) or (b) render it as a teacher-replayable dataset (gated by
    ``reuse_scope: weights`` + a recorded per-provider ToS check).

  - **Channel C — self-distillation** (wired in the teacher; see
    :mod:`autocode.anvil.teacher.loop`).

Copycat submodules:
  - :mod:`autocode.anvil.registry`  — the authorization registry (the hard gate).
  - :mod:`autocode.anvil.census`    — the capability model + ``--help`` parser.
  - :mod:`autocode.anvil.targets`   — concrete census collectors (``puku-cli``).
  - :mod:`autocode.anvil.manifest`  — introspects AutoCode's own CLI surface.
  - :mod:`autocode.anvil.gapdiff`   — diffs a target census against the manifest.
  - :mod:`autocode.anvil.propose`   — drafts a clean-room patch bundle for a gap.
  - :mod:`autocode.anvil.gate`      — applies a bundle's scoped checks; scores it.
  - :mod:`autocode.anvil.promote`   — records the promotion in the audit log.
  - :mod:`autocode.anvil.copycat`   — Channel B (outcome distillation): eval-oracle
                                      + distillation branches.
  - :mod:`autocode.anvil.cli`       — the ``autocode anvil`` command surface.
"""

from __future__ import annotations

ANVIL_VERSION = "0.1.0"

__all__ = ["ANVIL_VERSION"]
