"""Teacher mode (PLAN_04) — the companion leg of Anvil.

Teacher mode is a **root-cause analyst grounded in an executable oracle**. It
takes a (weaker / failed) AutoCode *student* trajectory plus the verifier's
deterministic verdict, optionally contrasts it against a stronger *teacher*
trajectory (``puku-cli``), classifies the failure by the §4.4 taxonomy, and
emits a **teaching packet** with two distinct outputs:

1. a reversible **playbook delta** (online, ship first) — an ACE-style entry the
   runtime loads from the durable-memory plane (``.autocode/playbook/<lang>.md``);
2. a candidate **harness fix** (offline) — a prediction-contracted proposal that
   reuses the copycat patch-bundle / gate / promote machinery
   (:mod:`autocode.anvil.gate`, :mod:`autocode.anvil.promote`).

Both outputs share the same *primary* signal: the executable verdict
(``diff_applies``, ``build``, ``tests``, ``lint``, ``types``) — not an LLM
judge. The judge is demoted to a secondary style sub-score. See
:mod:`autocode.anvil.teacher.signal`.

The teacher-student loop (:mod:`autocode.anvil.teacher.loop`) runs both
``autocode`` (student) and ``puku-cli`` (teacher) headlessly through the local
gateway against the same task and oracle — that is "teacher mode, end to end".

Submodules
----------
* :mod:`autocode.anvil.teacher.schemas`    — trajectory / verdict / teaching-packet types.
* :mod:`autocode.anvil.teacher.verifier`   — the deterministic outcome oracle (G3).
* :mod:`autocode.anvil.teacher.taxonomy`   — the root-cause taxonomy + cluster ranking.
* :mod:`autocode.anvil.teacher.classifier` — deterministic root-cause classifier.
* :mod:`autocode.anvil.teacher.signal`     — the execution-first signal hierarchy.
* :mod:`autocode.anvil.teacher.playbook`   — ACE playbook (Curator / Pruner / Loader).
* :mod:`autocode.anvil.teacher.reflector`  — turns a trajectory+verdict into a packet.
* :mod:`autocode.anvil.teacher.recorder`   — parses raw runs into the trajectory schema.
* :mod:`autocode.anvil.teacher.runners`    — drives student / teacher headlessly.
* :mod:`autocode.anvil.teacher.loop`       — the teacher-student orchestrator.
"""

from __future__ import annotations

TEACHER_VERSION = "0.1.0"

__all__ = ["TEACHER_VERSION"]
