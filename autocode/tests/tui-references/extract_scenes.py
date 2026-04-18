"""Extract scene contracts from the canonical design bundle.

The bundle at ``tui-references/AutoCode TUI _standalone_.html`` is a Figma-style
self-contained HTML export. It ships three ``<script type="__bundler/...">``
payloads (``manifest``, ``template``, ``ext_resources``). The *template* payload
is the authoritative inner markup and contains 14 ``<template id="t-<scene>"
data-screen-label="NN Name">`` elements — one per reference scene.

This module pulls the template payload with ``html.parser`` + ``json.loads`` +
(conditionally) ``base64`` / ``zlib``, walks each ``<template>`` subtree, and
emits a structured manifest describing every scene:

- scene id and human label (from ``data-screen`` + ``data-screen-label``)
- list of anchor text strings (visible text inside the inner TUI frame)
- set of region classes present (``hud``, ``composer-wrap``, etc.) and their
  counts — the foundation for the predicates in ``predicates.py``

Stdlib only: no ``lxml``, no ``scikit-image``, no ``imagehash``.

Usage:

.. code-block:: bash

    uv run python autocode/tests/tui-references/extract_scenes.py \
        --html tui-references/"AutoCode TUI _standalone_.html" \
        --out autocode/tests/tui-references/manifest.yaml
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import zlib
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

_SCRIPT_RE = re.compile(
    r'<script\s+type="(?P<type>[^"]+)"[^>]*>(?P<body>.*?)</script>',
    re.DOTALL,
)

# Scenes we are fully populating in Slice 1; other 14-scene entries get stubbed.
_MVP_SCENES: frozenset[str] = frozenset({"ready", "active", "recovery", "narrow"})


@dataclass
class BundlerPayload:
    """Decoded content of a ``<script type="__bundler/...">`` tag."""

    manifest: dict[str, Any]
    template: str
    ext_resources: list[Any]


@dataclass
class SceneRecord:
    """One scene pulled from a ``<template>`` element in the bundle."""

    scene_id: str                       # e.g. "ready", "active", "recovery", "narrow"
    label: str                          # e.g. "01 Ready", "07 Recovery"
    page_number: int                    # parsed leading integer in the label
    populated: bool                     # True for the 4 MVP scenes; False = stubbed
    anchors: list[str] = field(default_factory=list)
    class_counts: dict[str, int] = field(default_factory=dict)
    region_classes: list[str] = field(default_factory=list)
    raw_inner_length: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "label": self.label,
            "page_number": self.page_number,
            "populated": self.populated,
            "anchors": list(self.anchors),
            "region_classes": list(self.region_classes),
            "class_counts": dict(self.class_counts),
            "raw_inner_length": self.raw_inner_length,
        }


# --------------------------------------------------------------------- parsing

def _extract_script_payload(html: str, tag_type: str) -> str:
    """Return the inner text of the first ``<script type="<tag_type>">`` tag."""
    for match in _SCRIPT_RE.finditer(html):
        if match.group("type") == tag_type:
            return match.group("body").strip()
    raise ValueError(f"script tag not found: type={tag_type!r}")


def _decode_manifest_entry(entry: dict[str, Any]) -> bytes:
    """Decode a single manifest entry. Mirrors the JS bundler loader."""
    data_b64 = entry.get("data", "")
    raw = base64.b64decode(data_b64)
    if entry.get("compressed"):
        # Bundler uses gzip; zlib with ``MAX_WBITS|16`` decodes gzip streams.
        raw = zlib.decompress(raw, zlib.MAX_WBITS | 16)
    return raw


def load_bundle(html_path: Path) -> BundlerPayload:
    """Parse the three ``__bundler/*`` script tags from ``html_path``."""
    source = html_path.read_text(encoding="utf-8")
    manifest_text = _extract_script_payload(source, "__bundler/manifest")
    template_text = _extract_script_payload(source, "__bundler/template")
    extres_text = _extract_script_payload(source, "__bundler/ext_resources")

    manifest = json.loads(manifest_text)
    template = json.loads(template_text)
    ext_resources = json.loads(extres_text) if extres_text else []

    if not isinstance(manifest, dict):
        raise ValueError("manifest payload is not an object")
    if not isinstance(template, str):
        raise ValueError("template payload is not a string")
    if not isinstance(ext_resources, list):
        raise ValueError("ext_resources payload is not an array")

    return BundlerPayload(
        manifest=manifest,
        template=template,
        ext_resources=ext_resources,
    )


# ----------------------------------------------------------------- scene walk

class _SceneCollector(HTMLParser):
    """Collect per-``<template>`` subtrees keyed by the ``id`` attribute.

    Tracks *only* nested ``<template>`` depth — counting every tag confuses the
    state machine when inner markup contains void/self-closing elements whose
    matching ends html.parser may or may not synthesize.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._active_template: str | None = None
        self._attrs: dict[str, str] = {}
        self._template_depth: int = 0
        self._buffer: list[str] = []
        self.templates: dict[str, dict[str, Any]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "template":
            if self._active_template is None:
                attrs_d: dict[str, str] = {k: (v or "") for k, v in attrs}
                template_id = attrs_d.get("id", "")
                if template_id.startswith("t-"):
                    self._active_template = template_id
                    self._attrs = attrs_d
                    self._template_depth = 0
                    self._buffer = []
                return
            # Nested <template> inside an already-active template — rare, but
            # we preserve it in the buffer and deepen the close-match counter.
            self._template_depth += 1
            self._buffer.append(self._reconstruct_starttag(tag, attrs))
            return
        if self._active_template is not None:
            self._buffer.append(self._reconstruct_starttag(tag, attrs))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._active_template is not None:
            self._buffer.append(self._reconstruct_starttag(tag, attrs, self_closing=True))

    def handle_endtag(self, tag: str) -> None:
        if self._active_template is None:
            return
        if tag == "template":
            if self._template_depth == 0:
                self.templates[self._active_template] = {
                    "attrs": dict(self._attrs),
                    "inner": "".join(self._buffer),
                }
                self._active_template = None
                self._attrs = {}
                self._buffer = []
                return
            self._template_depth -= 1
            self._buffer.append("</template>")
            return
        self._buffer.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self._active_template is not None:
            self._buffer.append(data)

    @staticmethod
    def _reconstruct_starttag(
        tag: str,
        attrs: list[tuple[str, str | None]],
        *,
        self_closing: bool = False,
    ) -> str:
        parts = [tag]
        for name, value in attrs:
            if value is None:
                parts.append(name)
            else:
                safe = value.replace('"', "&quot;")
                parts.append(f'{name}="{safe}"')
        suffix = "/" if self_closing else ""
        return f"<{' '.join(parts)}{suffix}>"


class _TextAndClassCollector(HTMLParser):
    """Walk a template subtree and collect anchor text, class distribution,
    and the screen label from the inner ``<div class="host ...">`` element.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchor_texts: list[str] = []
        self.class_counts: dict[str, int] = {}
        self.screen_label: str = ""
        self._text_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = {k: (v or "") for k, v in attrs}
        classes = attrs_d.get("class", "")
        if classes:
            for token in classes.split():
                self.class_counts[token] = self.class_counts.get(token, 0) + 1
        # The screen label lives on the outermost <div class="host ...">.
        if not self.screen_label:
            label = attrs_d.get("data-screen-label", "")
            if label:
                self.screen_label = label

    def handle_endtag(self, tag: str) -> None:  # noqa: ARG002 — tag unused by design
        pass

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self._text_buffer.append(stripped)

    def finalize(self) -> None:
        joined = " ".join(self._text_buffer)
        self.anchor_texts = [
            chunk.strip()
            for chunk in re.split(r"\s{2,}|\n+", joined)
            if chunk.strip()
        ]


_REGION_CLASSES: frozenset[str] = frozenset(
    {
        "hud",
        "composer",
        "composer-wrap",
        "keybinds",
        "hint",
        "screen",
        "screen-mount",
        "titlebar",
        "tool",
        "diff",
        "recovery-card",
        "actions",
        "overlay",
        "palette",
        "narrow-tabs",
        "tab",
        "sys",
    }
)


def _collect_scene(template_id: str, attrs: dict[str, str], inner: str) -> SceneRecord:
    scene_id = template_id.removeprefix("t-")

    walker = _TextAndClassCollector()
    walker.feed(inner)
    walker.close()
    walker.finalize()

    label = walker.screen_label or attrs.get("data-screen-label", "")
    page_match = re.match(r"\s*(\d+)", label)
    page_number = int(page_match.group(1)) if page_match else 0

    region_classes = sorted(_REGION_CLASSES.intersection(walker.class_counts))

    return SceneRecord(
        scene_id=scene_id,
        label=label,
        page_number=page_number,
        populated=scene_id in _MVP_SCENES,
        anchors=walker.anchor_texts,
        class_counts=dict(walker.class_counts),
        region_classes=region_classes,
        raw_inner_length=len(inner),
    )


def extract_scenes(html_path: Path) -> list[SceneRecord]:
    """Return the ordered scene list from the design bundle."""
    bundle = load_bundle(html_path)
    collector = _SceneCollector()
    collector.feed(bundle.template)
    collector.close()

    scenes: list[SceneRecord] = []
    for tid, payload in collector.templates.items():
        attrs = payload["attrs"]
        inner = payload["inner"]
        scenes.append(_collect_scene(tid, attrs, inner))

    scenes.sort(key=lambda s: (s.page_number, s.scene_id))
    return scenes


# ----------------------------------------------------------------- yaml emit

def _yaml_escape(value: str) -> str:
    """Minimal YAML double-quoted escape. Stdlib has no safe-dumper."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def emit_manifest_yaml(scenes: list[SceneRecord]) -> str:
    """Hand-rolled YAML writer keeping Slice 1 dependency-free.

    Codex 1187 pushed back on adding parser-heavy deps; a small writer here is
    less surface area than pulling in ``PyYAML`` purely for this one file.
    """
    out: list[str] = [
        "# Auto-generated by autocode/tests/tui-references/extract_scenes.py.",
        "# Source of truth: tui-references/AutoCode TUI _standalone_.html",
        "# Do NOT edit by hand — re-run the extractor after updating the bundle.",
        "",
        "version: 1",
        f"scene_count: {len(scenes)}",
        "scenes:",
    ]
    for scene in scenes:
        out.append(f"  - scene_id: {scene.scene_id}")
        out.append(f'    label: "{_yaml_escape(scene.label)}"')
        out.append(f"    page_number: {scene.page_number}")
        out.append(f"    populated: {'true' if scene.populated else 'false'}")
        out.append(f"    raw_inner_length: {scene.raw_inner_length}")
        if scene.region_classes:
            out.append("    region_classes:")
            for cls in scene.region_classes:
                out.append(f"      - {cls}")
        else:
            out.append("    region_classes: []")
        if scene.anchors:
            out.append("    anchors:")
            for anchor in scene.anchors:
                out.append(f'      - "{_yaml_escape(anchor)}"')
        else:
            out.append("    anchors: []")
        if scene.class_counts:
            out.append("    class_counts:")
            for cls in sorted(scene.class_counts):
                out.append(f"      {cls}: {scene.class_counts[cls]}")
        else:
            out.append("    class_counts: {}")
    out.append("")
    return "\n".join(out)


# ------------------------------------------------------------------- entrypoint

def _default_html_path() -> Path:
    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    return repo_root / "tui-references" / "AutoCode TUI _standalone_.html"


def _default_out_path() -> Path:
    return Path(__file__).resolve().parent / "manifest.yaml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--html", type=Path, default=_default_html_path(),
                        help="Path to the self-contained HTML bundle")
    parser.add_argument("--out", type=Path, default=_default_out_path(),
                        help="Path to write manifest.yaml")
    parser.add_argument("--stdout", action="store_true",
                        help="Print YAML to stdout instead of writing to --out")
    args = parser.parse_args(argv)

    if not args.html.is_file():
        print(f"ERROR: HTML bundle not found: {args.html}", file=sys.stderr)
        return 2

    scenes = extract_scenes(args.html)
    yaml_text = emit_manifest_yaml(scenes)

    if args.stdout:
        sys.stdout.write(yaml_text)
    else:
        args.out.write_text(yaml_text, encoding="utf-8")
        populated = sum(1 for s in scenes if s.populated)
        print(
            f"wrote {len(scenes)} scenes "
            f"({populated} populated, {len(scenes) - populated} stubbed) "
            f"→ {args.out.relative_to(Path.cwd()) if args.out.is_absolute() else args.out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
