"""The E1002's e-paper canvas and its Spectra 6 dither, ported from the SDK's
esp32/main/epaper_status.c (pinned revision in firmware/sdk.lock)."""

from __future__ import annotations

import sys
from array import array

from PIL import Image, ImageDraw

from ..render import INKS, font

W, H = 800, 480

# s_inks[] in epaper_status.c: controller code and colour, black and white first.
INK_CODES = (0, 1, 2, 3, 5, 6)
_INK_Y = [(77 * r + 150 * g + 29 * b) >> 8 for r, g, b in INKS]


def _cdiv16(v: int) -> int:
    """C's `v / 16` on ints: truncates toward zero."""
    return v // 16 if v >= 0 else -((-v) // 16)


def nearest_ink(r: int, g: int, b: int) -> int:
    """Index into INKS, exactly as nearest_ink() in the firmware."""
    y = (77 * r + 150 * g + 29 * b) >> 8
    best, best_d = 0, 0
    for i, (ir, ig, ib) in enumerate(INKS):
        iy = _INK_Y[i]
        dy, du, dv = y - iy, (r - y) - (ir - iy), (b - y) - (ib - iy)
        d = dy * dy + du * du + dv * dv
        if i == 0 or d < best_d:
            best, best_d = i, d
    return best


def dither_color(canvas: array, w: int = W, h: int = H) -> bytearray:
    """dither_color(): native RGB565 canvas -> one INKS index per pixel."""
    out = bytearray(w * h)
    cur = [0] * (3 * (w + 2))
    nearest_cache: dict[tuple[int, int, int], int] = {}
    for y in range(h):
        nxt = [0] * (3 * (w + 2))
        base = y * w
        for x in range(w):
            px = canvas[base + x]
            r, g, b = (px >> 11) & 0x1F, (px >> 5) & 0x3F, px & 0x1F
            o = 3 * (x + 1)
            c0 = (r << 3 | r >> 2) + cur[o]
            c1 = (g << 2 | g >> 4) + cur[o + 1]
            c2 = (b << 3 | b >> 2) + cur[o + 2]
            c0 = -128 if c0 < -128 else 383 if c0 > 383 else c0
            c1 = -128 if c1 < -128 else 383 if c1 > 383 else c1
            c2 = -128 if c2 < -128 else 383 if c2 > 383 else c2
            key = (c0, c1, c2)
            ink = nearest_cache.get(key)
            if ink is None:
                ink = nearest_cache[key] = nearest_ink(c0, c1, c2)
            out[base + x] = ink
            ir, ig, ib = INKS[ink]
            for k, e in ((0, c0 - ir), (1, c1 - ig), (2, c2 - ib)):
                if e:
                    cur[3 * (x + 2) + k] += _cdiv16(e * 7)
                    nxt[3 * x + k] += _cdiv16(e * 3)
                    nxt[3 * (x + 1) + k] += _cdiv16(e * 5)
                    nxt[3 * (x + 2) + k] += _cdiv16(e)
        cur = nxt
    return out


def _palette() -> list[int]:
    return [c for ink in INKS for c in ink] + [0] * 3 * (256 - len(INKS))


class Panel:
    """Canvas plus what the panel currently shows."""

    def __init__(self, fixed: bool = False, title: str = "Muse"):
        self.fixed = fixed
        self.title = title
        self.canvas = array("H", [0xFFFF]) * (W * H)
        self.image_mode = False
        self.dirty = False
        self.refreshes = 0
        self.shown = self._status_screen()

    def _status_screen(self) -> Image.Image:
        # Stand-in for the firmware's status screen (name, character, status line).
        im = Image.new("RGB", (W, H), INKS[1])
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        d.ellipse((340, 120, 460, 240), fill=INKS[2], outline=INKS[0], width=4)
        d.ellipse((370, 160, 384, 174), fill=INKS[0])
        d.ellipse((416, 160, 430, 174), fill=INKS[0])
        d.arc((370, 170, 430, 220), 20, 160, fill=INKS[0], width=4)
        f = font(36, True)
        tw = d.textlength(self.title, font=f)
        d.text(((W - tw) / 2, 270), self.title, font=f, fill=INKS[0])
        s = "Ready (virtual reTerminal E1002)"
        f2 = font(22)
        d.text(((W - d.textlength(s, font=f2)) / 2, 326), s, font=f2, fill=INKS[4])
        return im

    def draw_rect(self, x: int, y: int, w: int, h: int, be: bytes) -> bool:
        """led_status_draw_rect(): `be` is RGB565, high byte first."""
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > W or y + h > H or len(be) != w * h * 2:
            return False
        if not self.image_mode:
            self.image_mode = True
            self.canvas = array("H", [0xFFFF]) * (W * H)
        vals = array("H")
        vals.frombytes(be)
        # array("H") reads native order, as the firmware's memcpy + uint16_t read
        # does on the little-endian ESP32-S3. Fixed firmware decodes high byte first.
        if self.fixed == (sys.byteorder == "little"):
            vals.byteswap()
        for r in range(h):
            start = (y + r) * W + x
            self.canvas[start:start + w] = vals[r * w:(r + 1) * w]
        self.dirty = True
        return True

    def draw_done(self) -> None:
        """led_status_draw_done(): dither and refresh, if anything was drawn."""
        if not (self.image_mode and self.dirty):
            return
        self.dirty = False
        idx = dither_color(self.canvas)
        im = Image.frombytes("P", (W, H), bytes(idx))
        im.putpalette(_palette())
        self.shown = im.convert("RGB")
        self.refreshes += 1

    def show_animation(self) -> None:
        self.image_mode = False
        self.shown = self._status_screen()
        self.refreshes += 1
