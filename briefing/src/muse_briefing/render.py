"""Draw a briefing as an 800x480 picture for the reTerminal E1002.

The E1002's Spectra 6 panel has six inks. The firmware Floyd-Steinberg
dithers whatever it gets down to them, which turns anti-aliased text and soft
colours into speckle. So everything here is drawn with the six exact ink
colours only (text without anti-aliasing) and snapped to them at the end:
pixels that already sit on an ink come through the device's dither unchanged
and the panel shows exactly this picture.
"""

from __future__ import annotations

import math
import os
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .model import Briefing, Weather

WIDTH, HEIGHT = 800, 480

# The inks, as the firmware's epaper_status.c s_inks[] defines them.
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
INKS = (BLACK, WHITE, YELLOW, RED, BLUE, GREEN)

_FONT_CANDIDATES = {
    False: [
        os.environ.get("BRIEFING_FONT", ""),
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ],
    True: [
        os.environ.get("BRIEFING_FONT_BOLD", ""),
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ],
}


@lru_cache(maxsize=None)
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES[bold]:
        if not path:
            continue
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)  # Pillow's bundled font


def fit(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, width: int) -> str:
    """Cut text to fit `width` pixels, ending in an ellipsis if it had to."""
    if draw.textlength(text, font=f) <= width:
        return text
    while text and draw.textlength(text + "…", font=f) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _deg(v: float | None) -> str:
    return "–" if v is None else f"{round(v)}°"


def render(b: Briefing) -> Image.Image:
    im = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"  # no anti-aliasing: every text pixel is a whole ink

    _header(d, b)
    note_h = 44 if b.note else 0
    body_bottom = HEIGHT - note_h

    # Left: today's calendar
    left, col_w = 28, 420
    y = 104
    d.text((left, y), "TODAY", font=font(22, True), fill=RED)
    y += 38
    if not b.events:
        d.text((left, y), "Nothing on the calendar", font=font(26), fill=BLACK)
    for e in b.events:
        if y + 40 > body_bottom - 8:
            break
        time_w = 88
        label = e.time or "All day"
        d.text((left, y), label, font=font(24 if e.time else 20, True), fill=RED if e.time else BLUE)
        text = e.title + (f" · {e.location}" if e.location else "")
        d.text((left + time_w, y), fit(d, text, font(24), col_w - time_w), font=font(24), fill=BLACK)
        y += 44

    # Divider
    d.rectangle((462, 104, 464, body_bottom - 20), fill=BLACK)

    # Right: weather, then to-dos
    rx, rw = 488, WIDTH - 488 - 24
    y = 104
    if b.weather:
        y = _weather(d, b.weather, rx, y, rw)
    y += 14
    d.text((rx, y), "TO-DO", font=font(22, True), fill=GREEN)
    y += 36
    if not b.todos:
        d.text((rx, y), "All clear", font=font(24), fill=BLACK)
    for t in b.todos:
        if y + 36 > body_bottom - 8:
            break
        d.rectangle((rx, y + 4, rx + 20, y + 24), outline=BLACK, width=3)
        d.text((rx + 32, y), fit(d, t, font(24), rw - 32), font=font(24), fill=BLACK)
        y += 38

    if b.note:
        d.rectangle((0, HEIGHT - note_h, WIDTH, HEIGHT), fill=YELLOW)
        d.text((28, HEIGHT - note_h + 9), fit(d, b.note, font(24, True), WIDTH - 56),
               font=font(24, True), fill=BLACK)

    return snap_to_inks(im)


def _header(d: ImageDraw.ImageDraw, b: Briefing) -> None:
    d.rectangle((0, 0, WIDTH, 84), fill=BLUE)
    d.text((28, 10), fit(d, b.title, font(20, True), 460), font=font(20, True), fill=YELLOW)
    date_text = f"{b.day:%A} {b.day.day} {b.day:%B}"
    d.text((28, 36), date_text, font=font(36, True), fill=WHITE)
    if b.weather and b.weather.now is not None:
        now = _deg(b.weather.now)
        f = font(48, True)
        w = d.textlength(now, font=f)
        d.text((WIDTH - 28 - w, 12), now, font=f, fill=WHITE)
    if b.updated:
        s = f"Updated {b.updated}"
        f = font(16)
        w = d.textlength(s, font=f)
        x = WIDTH - 28 - w
        if b.weather and b.weather.now is not None:
            x -= 150
        d.text((x, 54), s, font=f, fill=WHITE)


def _weather(d: ImageDraw.ImageDraw, w: Weather, x: int, y: int, width: int) -> int:
    icon(d, w.icon, x, y, 76)
    tx = x + 92
    d.text((tx, y + 2), fit(d, f"{_deg(w.high)} / {_deg(w.low)}", font(34, True), width - 92),
           font=font(34, True), fill=BLACK)
    d.text((tx, y + 44), fit(d, w.summary, font(22), width - 92), font=font(22), fill=BLACK)
    y += 88
    if w.precip is not None:
        colour = BLUE if w.precip >= 40 else BLACK
        text = f"Rain {w.precip}%" + (" – umbrella!" if w.precip >= 60 else "")
        d.text((x, y), fit(d, text, font(20, w.precip >= 60), width), font=font(20, w.precip >= 60), fill=colour)
        y += 30
    return y


def icon(d: ImageDraw.ImageDraw, kind: str, x: int, y: int, s: int) -> None:
    """Flat weather glyphs in pure inks, s x s at (x, y)."""
    def sun(cx: int, cy: int, r: int) -> None:
        for i in range(8):
            a = i * math.pi / 4
            x0, y0 = cx + (r + 4) * math.cos(a), cy + (r + 4) * math.sin(a)
            x1, y1 = cx + (r + 12) * math.cos(a), cy + (r + 12) * math.sin(a)
            d.line((x0, y0, x1, y1), fill=RED, width=4)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=YELLOW, outline=RED, width=3)

    def cloud(cx: int, cy: int, w: int) -> None:
        h = w // 2
        parts = [
            (cx - w // 2, cy - h // 4, cx, cy + h // 2),
            (cx - w // 4, cy - h // 2 - 4, cx + w // 4, cy + h // 3),
            (cx, cy - h // 4, cx + w // 2, cy + h // 2),
        ]
        for p in parts:
            d.ellipse(p, fill=BLACK)
        for p in parts:
            d.ellipse((p[0] + 3, p[1] + 3, p[2] - 3, p[3] - 3), fill=WHITE)
        d.rectangle((cx - w // 2 + 16, cy + h // 2 - 3, cx + w // 2 - 16, cy + h // 2), fill=BLACK)

    c = s // 2
    if kind == "sun":
        sun(x + c, y + c, s // 4)
    elif kind == "partly":
        sun(x + c - 10, y + c - 12, s // 5)
        cloud(x + c + 6, y + c + 8, s - 18)
    elif kind == "cloud":
        cloud(x + c, y + c, s - 8)
    elif kind == "fog":
        for i in range(4):
            d.rectangle((x + 6 + (i % 2) * 8, y + 16 + i * 14, x + s - 6 - (i % 2) * 8, y + 21 + i * 14), fill=BLACK)
    elif kind in ("rain", "snow", "storm"):
        cloud(x + c, y + c - 10, s - 8)
        base = y + c + 18
        if kind == "rain":
            for i in range(4):
                px = x + 14 + i * 16
                d.line((px + 4, base, px - 2, base + 14), fill=BLUE, width=4)
        elif kind == "snow":
            for i in range(4):
                px = x + 16 + i * 16
                d.ellipse((px - 4, base + 4, px + 4, base + 12), fill=BLUE)
        else:
            pts = [(x + c + 4, base - 4), (x + c - 8, base + 12), (x + c + 2, base + 12), (x + c - 6, base + 26)]
            d.line(pts, fill=YELLOW, width=5)
            d.line(pts, fill=RED, width=2)


def _palette_image() -> Image.Image:
    pal = Image.new("P", (1, 1))
    pal.putpalette([c for ink in INKS for c in ink] + [0] * 3 * (256 - len(INKS)))
    return pal


def _ink_indices(im: Image.Image) -> Image.Image:
    return im.convert("RGB").quantize(palette=_palette_image(), dither=Image.Dither.NONE)


def snap_to_inks(im: Image.Image) -> Image.Image:
    """Map every pixel to its nearest ink with no dithering."""
    return _ink_indices(im).convert("RGB")


def _rgb565(c: tuple[int, int, int]) -> int:
    return ((c[0] >> 3) << 11) | ((c[1] >> 2) << 5) | (c[2] >> 3)


_HI = bytes((_rgb565(INKS[i]) >> 8) if i < len(INKS) else 0 for i in range(256))
_LO = bytes((_rgb565(INKS[i]) & 0xFF) if i < len(INKS) else 0 for i in range(256))


def to_rgb565(im: Image.Image) -> bytes:
    """Raw RGB565, high byte first, whole rows: what display.draw_url takes
    besides baseline JPEG. 800x480 comes to 768,000 bytes. Pixels are snapped
    to the nearest ink first, so pass an image from render()."""
    if im.size != (WIDTH, HEIGHT):
        raise ValueError(f"image must be {WIDTH}x{HEIGHT}")
    idx = _ink_indices(im).tobytes()
    out = bytearray(len(idx) * 2)
    out[0::2] = idx.translate(_HI)
    out[1::2] = idx.translate(_LO)
    return bytes(out)
