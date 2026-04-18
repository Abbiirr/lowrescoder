"""Unit tests for the visual-snapshot differ.

The capture + rendering pipeline is covered by its own runner script; these
tests exercise the pure-Python diff logic so regressions in tolerance,
image-size mismatch, and highlight-output behavior are caught fast.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from PIL import Image

_DIFFER = Path(__file__).resolve().parents[1] / "vhs" / "differ.py"
_spec = importlib.util.spec_from_file_location("vhs_differ", _DIFFER)
assert _spec and _spec.loader
differ = importlib.util.module_from_spec(_spec)
sys.modules["vhs_differ"] = differ
_spec.loader.exec_module(differ)

diff_images = differ.diff_images
DiffReport = differ.DiffReport


def _make_png(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (40, 40)) -> Path:
    img = Image.new("RGB", size, color)
    img.save(path, format="PNG")
    return path


def test_identical_images_zero_mismatch(tmp_path: Path) -> None:
    a = _make_png(tmp_path / "a.png", (128, 128, 128))
    b = _make_png(tmp_path / "b.png", (128, 128, 128))
    report = diff_images(a, b)
    assert report.mismatched_pixels == 0
    assert report.mismatch_ratio == 0.0
    assert report.within_tolerance(pixel_ratio=0.0)


def test_totally_different_images_full_mismatch(tmp_path: Path) -> None:
    a = _make_png(tmp_path / "a.png", (0, 0, 0))
    b = _make_png(tmp_path / "b.png", (255, 255, 255))
    report = diff_images(a, b)
    assert report.mismatched_pixels == report.total_pixels
    assert report.mismatch_ratio == 1.0
    assert report.max_channel_delta == 255


def test_size_mismatch_raises(tmp_path: Path) -> None:
    a = _make_png(tmp_path / "a.png", (0, 0, 0), size=(40, 40))
    b = _make_png(tmp_path / "b.png", (0, 0, 0), size=(50, 50))
    with pytest.raises(ValueError):
        diff_images(a, b)


def test_threshold_tolerates_small_delta(tmp_path: Path) -> None:
    a = _make_png(tmp_path / "a.png", (100, 100, 100))
    b = _make_png(tmp_path / "b.png", (105, 105, 105))  # Δ=5 per channel
    report = diff_images(a, b, threshold=10)
    assert report.mismatched_pixels == 0
    assert report.within_tolerance()


def test_threshold_flags_large_delta(tmp_path: Path) -> None:
    a = _make_png(tmp_path / "a.png", (100, 100, 100))
    b = _make_png(tmp_path / "b.png", (150, 150, 150))  # Δ=50
    report = diff_images(a, b, threshold=10)
    assert report.mismatched_pixels > 0
    assert not report.within_tolerance(pixel_ratio=0.0)


def test_writes_diff_image_when_requested(tmp_path: Path) -> None:
    a = _make_png(tmp_path / "a.png", (0, 0, 0))
    b = _make_png(tmp_path / "b.png", (255, 255, 255))
    diff_out = tmp_path / "diff.png"
    report = diff_images(a, b, diff_out=diff_out)
    assert diff_out.is_file()
    assert report.diff_image == diff_out


def test_does_not_write_diff_image_by_default(tmp_path: Path) -> None:
    a = _make_png(tmp_path / "a.png", (0, 0, 0))
    b = _make_png(tmp_path / "b.png", (255, 255, 255))
    report = diff_images(a, b)
    assert report.diff_image is None


def test_within_tolerance_default_is_one_percent(tmp_path: Path) -> None:
    a = _make_png(tmp_path / "a.png", (0, 0, 0), size=(100, 100))
    b_path = tmp_path / "b.png"
    # Make B with ~50 pixels changed (0.5% of 10000), all white
    img = Image.new("RGB", (100, 100), (0, 0, 0))
    pixels = img.load()
    for i in range(50):
        pixels[i, 0] = (255, 255, 255)
    img.save(b_path, format="PNG")

    report = diff_images(a, b_path)
    assert report.mismatched_pixels == 50
    assert report.within_tolerance()  # 0.5% < 1% default
    assert not report.within_tolerance(pixel_ratio=0.001)  # 0.1% cap


def test_dataclass_ratio_math() -> None:
    report = DiffReport(
        reference=Path("/tmp/r"),
        candidate=Path("/tmp/c"),
        mismatched_pixels=25,
        total_pixels=100,
        max_channel_delta=200,
        diff_image=None,
    )
    assert report.mismatch_ratio == 0.25
    assert report.within_tolerance(pixel_ratio=0.3)
    assert not report.within_tolerance(pixel_ratio=0.2)
