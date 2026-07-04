"""Named capture presets for the 14 reference scenes.

These presets are intentionally honest about current coverage:

- ``direct`` means the current product has a deterministic live path that
  produces a scene worth comparing directly.
- ``approximate`` means the current product can show a nearby surface, but not
  the full reference scene yet.
- ``blocked`` means there is no truthful current capture because the product
  surface or fixture path does not exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenePreset:
    scene_id: str
    label: str
    reference_page: str
    capture_mode: str
    note: str
    steps: tuple[str | float, ...] = ()
    rows: int = 50
    cols: int = 160
    boot_budget: float = 4.0
    drain_quiet: float = 1.0
    drain_maxwait: float = 4.0

    @property
    def runnable(self) -> bool:
        return self.capture_mode != "blocked"


SCENE_PRESETS: dict[str, ScenePreset] = {
    "ready": ScenePreset(
        scene_id="ready",
        label="01 Ready",
        reference_page="0001",
        capture_mode="direct",
        note="Idle startup surface with header, transcript body, composer, and footer.",
        steps=(0.8,),
    ),
    "active": ScenePreset(
        scene_id="active",
        label="02 Active",
        reference_page="0002",
        capture_mode="direct",
        note=(
            "Mid-run working state using the slow fixture so the spinner and "
            "active badge remain visible before completion."
        ),
        steps=("refactor parser.ts to safely handle missing imports and run tests\r", 0.6),
        drain_quiet=0.2,
        drain_maxwait=0.3,
    ),
    "multi": ScenePreset(
        scene_id="multi",
        label="03 Multitasking",
        reference_page="0003",
        capture_mode="direct",
        note="Dedicated multitasking / queue-pressure surface via `/multi`.",
        steps=(0.8, "/multi\r", 1.0),
    ),
    "plan": ScenePreset(
        scene_id="plan",
        label="04 Plan",
        reference_page="0004",
        capture_mode="direct",
        note="Dedicated plan surface opened via `/plan`.",
        steps=(0.8, "/plan\r", 1.2),
    ),
    "review": ScenePreset(
        scene_id="review",
        label="05 Review",
        reference_page="0005",
        capture_mode="direct",
        note="Dedicated review surface opened via `/review`.",
        steps=(0.8, "/review\r", 1.0),
    ),
    "cc": ScenePreset(
        scene_id="cc",
        label="06 Command center",
        reference_page="0006",
        capture_mode="direct",
        note="Dedicated command-center surface opened via `/cc`.",
        steps=(0.8, "/cc\r", 1.0),
    ),
    "recovery": ScenePreset(
        scene_id="recovery",
        label="07 Recovery",
        reference_page="0007",
        capture_mode="direct",
        note="Halted state with visible recovery actions from the backend error path.",
        steps=("__HALT_FAILURE__\r", 0.5),
    ),
    "restore": ScenePreset(
        scene_id="restore",
        label="08 Restore",
        reference_page="0008",
        capture_mode="direct",
        note="Dedicated restore/checkpoint browser opened via `/restore`.",
        steps=(0.8, "/restore\r", 1.0),
    ),
    "sessions": ScenePreset(
        scene_id="sessions",
        label="09 Sessions",
        reference_page="0009",
        capture_mode="direct",
        note="Direct session-picker overlay from `/sessions` or `/resume`.",
        steps=(0.8, "/sessions\r", 2.0),
    ),
    "palette": ScenePreset(
        scene_id="palette",
        label="10 Palette",
        reference_page="0010",
        capture_mode="direct",
        note="Direct command-palette overlay via `Ctrl+K`.",
        steps=(0.8, "\x0b", 0.6),
    ),
    "diff": ScenePreset(
        scene_id="diff",
        label="11 Diff focus",
        reference_page="0011",
        capture_mode="direct",
        note="Dedicated diff-focus surface opened via `/diff`.",
        steps=(0.8, "/diff\r", 1.0),
    ),
    "grep": ScenePreset(
        scene_id="grep",
        label="12 Search",
        reference_page="0012",
        capture_mode="direct",
        note="Dedicated search surface opened via `/grep`.",
        steps=(0.8, "/grep\r", 1.0),
    ),
    "escalation": ScenePreset(
        scene_id="escalation",
        label="13 Escalation",
        reference_page="0013",
        capture_mode="direct",
        note="Dedicated escalation surface opened via `/escalation`.",
        steps=(0.8, "/escalation\r", 1.0),
    ),
    "narrow": ScenePreset(
        scene_id="narrow",
        label="14 Narrow",
        reference_page="0014",
        capture_mode="direct",
        note="Narrow-width idle surface to expose wrapping and geometry pressure.",
        steps=(0.8,),
        rows=30,
        cols=68,
    ),
}


def scene_presets() -> dict[str, ScenePreset]:
    return dict(SCENE_PRESETS)


def get_scene_preset(name: str) -> ScenePreset:
    return SCENE_PRESETS[name]
