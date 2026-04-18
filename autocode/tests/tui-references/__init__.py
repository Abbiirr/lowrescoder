"""Reference-driven TUI testing harness.

Parses the canonical design bundle at ``tui-references/AutoCode TUI _standalone_.html``
into a scene manifest and runs deterministic parity predicates against the live
Go TUI captured via the existing ``autocode/tests/tui-comparison/`` PTY substrate.

Slice 1 contents:

- ``extract_scenes``: stdlib HTML parse of the bundler wrapper + per-scene anchor
  and region extraction; emits ``manifest.yaml``
- ``manifest.yaml``: 14 scenes listed, 4 MVP populated (01 ready, 02 active,
  07 recovery, 14 narrow), other 10 stubbed
- ``predicates``: scene-contract predicates consuming a pyte Screen
- ``test_reference_scenes``: 4-scene live PTY parity tests
"""

__all__: list[str] = []
