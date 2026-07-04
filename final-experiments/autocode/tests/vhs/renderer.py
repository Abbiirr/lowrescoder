"""Render a pyte Screen to a PNG via Pillow.

The rendering is cell-based: every terminal cell becomes a fixed-size box
painted with the cell's background color and character. Monospace is
required so font width per cell stays stable across captures.

Uses DejaVu Sans Mono by default (ships with most Linux installs); override
with ``font_path`` if needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pyte
from PIL import Image, ImageDraw, ImageFont

# Strip kitty-protocol keyboard sequences before pyte sees them. These are
# CSI-terminated with `u` and pyte mis-parses them, leaking `0;1u`-style
# literals into the rendered cell grid. BubbleTea v2 emits/echoes these on
# startup; without this filter the PNG shows garbage text at the cursor.
_KITTY_KEYBOARD_PROTO = re.compile(rb"\x1b\[[?>=<0-9;:]*u")

DEFAULT_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
DEFAULT_FONT_SIZE = 14
DEFAULT_PADDING = 8

# Minimal 16-color ANSI palette used when the cell's color is a named color.
# Pyte emits color as either a hex string ("ff0000"), or a named token like
# "red" / "brightred" / "default". Unknown or "default" → foreground uses
# DEFAULT_FG, background uses DEFAULT_BG.
DEFAULT_FG = (204, 204, 204)
DEFAULT_BG = (12, 12, 12)

_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "red": (205, 49, 49),
    "green": (13, 188, 121),
    "yellow": (229, 229, 16),
    "blue": (36, 114, 200),
    "magenta": (188, 63, 188),
    "cyan": (17, 168, 205),
    "white": (229, 229, 229),
    "brightblack": (102, 102, 102),
    "brightred": (241, 76, 76),
    "brightgreen": (35, 209, 139),
    "brightyellow": (245, 245, 67),
    "brightblue": (59, 142, 234),
    "brightmagenta": (214, 112, 214),
    "brightcyan": (41, 184, 219),
    "brightwhite": (229, 229, 229),
}


def _resolve_color(value: str, *, is_background: bool) -> tuple[int, int, int]:
    """Map a pyte color token to RGB."""
    if not value or value == "default":
        return DEFAULT_BG if is_background else DEFAULT_FG
    if value in _NAMED_COLORS:
        return _NAMED_COLORS[value]
    # pyte emits hex strings without '#'
    try:
        if len(value) == 6:
            return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except ValueError:
        pass
    return DEFAULT_BG if is_background else DEFAULT_FG


@dataclass
class RenderOptions:
    font_path: str = DEFAULT_FONT
    font_size: int = DEFAULT_FONT_SIZE
    padding: int = DEFAULT_PADDING
    background: tuple[int, int, int] = DEFAULT_BG


def render_screen_to_png(
    screen: pyte.Screen,
    output: Path,
    *,
    options: RenderOptions | None = None,
) -> Path:
    """Render a pyte Screen to a PNG file.

    Returns the output Path for chaining.
    """
    opts = options or RenderOptions()
    font = ImageFont.truetype(opts.font_path, opts.font_size)

    # Measure a representative cell (mono font — every cell is the same size).
    bbox = font.getbbox("M")
    cell_w = bbox[2] - bbox[0]
    cell_h = int((bbox[3] - bbox[1]) * 1.4)  # add small line-height cushion

    img_w = cell_w * screen.columns + opts.padding * 2
    img_h = cell_h * screen.lines + opts.padding * 2

    img = Image.new("RGB", (img_w, img_h), opts.background)
    draw = ImageDraw.Draw(img)

    for y, row in enumerate(screen.buffer.values()):
        for x in range(screen.columns):
            char = row[x] if x in row else None
            ch = char.data if char is not None else " "
            fg = _resolve_color(getattr(char, "fg", "default") if char else "default",
                                is_background=False)
            bg = _resolve_color(getattr(char, "bg", "default") if char else "default",
                                is_background=True)

            px = opts.padding + x * cell_w
            py = opts.padding + y * cell_h

            # Background fill per cell when it differs from the screen bg
            if bg != opts.background:
                draw.rectangle(
                    [px, py, px + cell_w, py + cell_h],
                    fill=bg,
                )

            if ch and ch != " ":
                draw.text((px, py), ch, font=font, fill=fg)

    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output, format="PNG", optimize=True)
    return output


def feed_ansi_to_screen(
    ansi: bytes,
    *,
    columns: int = 160,
    lines: int = 50,
) -> pyte.Screen:
    """Return a pyte Screen populated from an ANSI byte stream.

    Pre-filters kitty keyboard-protocol CSI-u sequences pyte can't parse,
    then feeds the rest into a fresh pyte Screen + ByteStream pair.
    """
    cleaned = _KITTY_KEYBOARD_PROTO.sub(b"", ansi)
    screen = pyte.Screen(columns, lines)
    stream = pyte.ByteStream(screen)
    stream.feed(cleaned)
    return screen
