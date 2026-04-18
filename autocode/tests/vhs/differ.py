"""Pillow-based pixel diff helper for TUI visual snapshots.

Returns a structured ``DiffReport`` and optionally writes the diff image
(red mask over differing pixels) so reviewers can see what changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops


@dataclass
class DiffReport:
    """Summary of a visual comparison."""

    reference: Path
    candidate: Path
    mismatched_pixels: int
    total_pixels: int
    max_channel_delta: int
    diff_image: Path | None

    @property
    def mismatch_ratio(self) -> float:
        if self.total_pixels == 0:
            return 0.0
        return self.mismatched_pixels / self.total_pixels

    def within_tolerance(self, *, pixel_ratio: float = 0.01) -> bool:
        """Return True if mismatch stays under ``pixel_ratio`` (default 1%)."""
        return self.mismatch_ratio <= pixel_ratio


def diff_images(
    reference: Path,
    candidate: Path,
    *,
    diff_out: Path | None = None,
    highlight_rgb: tuple[int, int, int] = (255, 0, 0),
    threshold: int = 10,
) -> DiffReport:
    """Compare two PNGs pixel-wise. Images must have the same size.

    ``threshold`` — per-channel delta below which a pixel is considered
    unchanged (tolerates tiny anti-alias jitter).
    """
    ref = Image.open(reference).convert("RGB")
    cand = Image.open(candidate).convert("RGB")
    if ref.size != cand.size:
        raise ValueError(
            f"size mismatch: reference={ref.size} vs candidate={cand.size}",
        )

    delta = ImageChops.difference(ref, cand)
    # Collapse three channels to per-pixel max delta via a grayscale reduction.
    # PIL's `getextrema()` on the result gives (min_max_channel, max_max_channel).
    max_channel = delta.convert("L", matrix=(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0))
    # The matrix above gives a luminance-weighted conversion; use ImageChops
    # max-of-channels instead for a true per-pixel max.
    r, g, b = delta.split()
    max_channel = ImageChops.lighter(ImageChops.lighter(r, g), b)
    max_delta = max_channel.getextrema()[1]

    # Binary mask: 1 where max_channel > threshold.
    mask = max_channel.point(lambda v: 255 if v > threshold else 0, mode="L")
    # Count mismatched pixels via histogram — O(bins), no Python per-pixel loop.
    mismatched = mask.histogram()[255]
    total = ref.size[0] * ref.size[1]

    diff_path: Path | None = None
    if diff_out is not None:
        # Composite: highlight_rgb where mask is set, dimmed reference elsewhere.
        highlight_layer = Image.new("RGB", ref.size, highlight_rgb)
        dim_ref = ref.point(lambda v: v // 3)
        diff_img = Image.composite(highlight_layer, dim_ref, mask)
        diff_out.parent.mkdir(parents=True, exist_ok=True)
        diff_img.save(diff_out, format="PNG", optimize=True)
        diff_path = diff_out

    return DiffReport(
        reference=reference,
        candidate=candidate,
        mismatched_pixels=mismatched,
        total_pixels=total,
        max_channel_delta=max_delta,
        diff_image=diff_path,
    )
