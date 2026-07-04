"""Channel B — outcome distillation (PLAN_05 §3).

Drives an authorized target on a task, captures the observable final artifact
(the diff / file set), keeps only the *verified* outcomes, and (separately,
gated by a recorded per-provider ToS check) renders a teacher-replayable form
for distillation. Two branches:

* :mod:`autocode.anvil.copycat.outcome` — the **eval-oracle branch**. Always
  safe (you are *comparing*, not training). Produces ``corpus@v<N>/<task>.json``
  with a ``verification`` block.
* :mod:`autocode.anvil.copycat.distill` — the **distillation branch**. Refused
  unless the registry grants ``reuse_scope: weights`` *and* a recorded
  per-provider ToS check is present. Produces ``dataset.jsonl``.

The hard discipline (PLAN_05 §3.3): **keep only verified outcomes**. An
unverified frontier diff is just a confident guess; storing it pollutes the
corpus. You are not trusting the teacher, you are trusting the tests.
"""

from __future__ import annotations

from autocode.anvil.copycat import distill, outcome

__all__ = ["distill", "outcome"]
