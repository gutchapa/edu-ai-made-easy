"""A software reTerminal E1002: what the Muse gadget firmware does with an image.

Mirrors the pinned SDK's esp32/main/image_fetch.c (download, JPEG scaling,
raw RGB565 rows) and esp32/main/epaper_status.c (canvas, Floyd-Steinberg to
the six Spectra 6 inks), so you can test without the hardware.

`fixed=False` (the default) reproduces the firmware as written, including how
led_status_draw_rect() copies high-byte-first pixels into a canvas that
dither_color() reads as native little-endian; `fixed=True` previews firmware
with that corrected (see docs/simulator.md).
"""

from .panel import Panel
from .device import VirtualReTerminal

__all__ = ["Panel", "VirtualReTerminal"]
