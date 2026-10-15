"""The gadget's commands, as the reTerminal E1002 firmware handles them.

display.draw_url mirrors esp32/main/image_fetch.c: http(s) only, redirects
kept on the same scheme, HTTP 200 only, a baseline JPEG (FF D8) shrunk by
1/2, 1/4 or 1/8 to fit and centred across from `row`, or raw RGB565 in whole
1600-byte rows; whatever arrived is shown even when the download fails.
"""

from __future__ import annotations

import io
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

from .panel import H, W, Panel
from .specs import COMMAND_SPECS, ROW_BYTES  # noqa: F401  (re-exported)

TIMEOUT_S = 30

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # handled by hand, like the firmware
        return None


def _open(url: str):
    opener = urllib.request.build_opener(_NoRedirect)
    https = url.lower().startswith("https://")
    for _ in range(5):
        try:
            return opener.open(urllib.request.Request(url, headers={"User-Agent": "virtual-reterminal"}),
                               timeout=TIMEOUT_S)
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                url = urllib.request.urljoin(url, e.headers["Location"])
                if url.lower().startswith("https://") != https:
                    raise ValueError("redirect changed scheme")
                continue
            raise ValueError(f"server answered HTTP {e.code}")
    raise ValueError("too many redirects")


class VirtualReTerminal:
    """Thread-safe: one download at a time, like the firmware."""

    def __init__(self, fixed: bool = False, refresh_seconds: float = 0.0,
                 temperature_c: float = 23.5, humidity: float = 48.0):
        self.panel = Panel(fixed=fixed)
        self.refresh_seconds = refresh_seconds
        self.sensors = (temperature_c, humidity)
        self._busy = threading.Lock()
        self._state = threading.Lock()
        self.log: list[dict] = []

    # -- Commands ----------------------------------------------------------

    def run(self, command: str, params: dict | None = None) -> dict:
        params = params or {}
        if command == "display.draw_url":
            result = self.draw_url(params)
        elif command == "display.show_animation":
            with self._state:
                self.panel.show_animation()
            result = {"ok": True}
        elif command == "sensors.read":
            t, rh = self.sensors
            result = {"ok": True, "payload": {
                "temperature": {"value": t, "unit": "C", "age_s": 1},
                "humidity": {"value": rh, "unit": "%", "age_s": 1}}}
        else:
            result = {"ok": False, "error": {"code": "unsupported", "message": f"unsupported command: {command}"}}
        self.log.append({"t": time.time(), "command": command, "params": params, "result": result})
        del self.log[:-50]
        return result

    def draw_url(self, params: dict) -> dict:
        url = params.get("url")
        if not isinstance(url, str) or not url:
            return _err("missing_param", "url is required")
        row = params.get("row", 0)
        if not isinstance(row, int) or row < 0 or row >= H:
            return _err("invalid_param", f"row must be 0..{H - 1}")
        if not self._busy.acquire(blocking=False):
            return _err("busy", "another image is downloading")
        try:
            return self._fetch_and_draw(url, row)
        finally:
            self._busy.release()

    def draw_bytes(self, data: bytes, row: int = 0) -> dict:
        """The drawing half of draw_url, for local files."""
        with self._state:
            return self._draw(data, row, time.monotonic())

    # -- Internals ---------------------------------------------------------

    def _fetch_and_draw(self, url: str, row: int) -> dict:
        lower = url.lower()
        if not (lower.startswith("http://") or lower.startswith("https://")):
            return _err("invalid_param", "url must be http:// or https://")
        started = time.monotonic()
        try:
            with _open(url) as r:
                data = r.read()
        except ValueError as e:
            return _err("download_failed", str(e))
        except (urllib.error.URLError, OSError) as e:
            reason = getattr(e, "reason", e)
            msg = "download timed out" if "timed out" in str(reason) else f"could not connect: {reason}"
            return _err("download_failed", msg)
        with self._state:
            return self._draw(data, row, started)

    def _draw(self, data: bytes, row: int, started: float) -> dict:
        p = self.panel
        if data[:2] == b"\xff\xd8":
            fmt = "jpeg"
            fail, w, h, scale = self._draw_jpeg(data, row)
        else:
            fmt, scale, w = "rgb565", 1, W
            fail, h = self._draw_raw(data, row)
        if self.refresh_seconds and p.image_mode and p.dirty:
            time.sleep(self.refresh_seconds)
        p.draw_done()  # shows what arrived, even after an error
        ms = int((time.monotonic() - started) * 1000)
        if fail:
            return _err("invalid_image", fail)
        return {"ok": True, "payload": {"format": fmt, "width": w, "height": h, "scale": scale,
                                        "bytes": len(data), "ms": ms}}

    def _draw_raw(self, data: bytes, row: int) -> tuple[str | None, int]:
        whole = len(data) // ROW_BYTES
        fits = min(whole, H - row)
        if fits:
            self.panel.draw_rect(0, row, W, fits, data[: fits * ROW_BYTES])
        if len(data) % ROW_BYTES:
            return "raw data must be whole rows of RGB565, high byte first", fits
        if whole > H - row:
            return "image runs past the last row", fits
        return None, fits

    def _draw_jpeg(self, data: bytes, row: int) -> tuple[str | None, int, int, int]:
        try:
            im = Image.open(io.BytesIO(data))
            im.load()
        except Exception:
            return "not a valid JPEG", 0, 0, 1
        if im.format != "JPEG":
            return "not a valid JPEG", 0, 0, 1
        if im.info.get("progressive") or im.info.get("progression"):
            return "unsupported JPEG: use baseline, not progressive", 0, 0, 1
        avail = H - row
        shift = 0
        while shift < 3 and ((im.width >> shift) > W or (im.height >> shift) > avail):
            shift += 1
        w, h = im.width >> shift, im.height >> shift
        if w > W or h > avail:
            return "JPEG is too large even at 1/8 scale", w, h, 1 << shift
        if shift:
            im = im.reduce(1 << shift)
            im = im.crop((0, 0, w, h)) if im.size != (w, h) else im
        rgb = im.convert("RGB").tobytes()
        be = bytearray(w * h * 2)
        for i in range(w * h):
            r, g, b = rgb[3 * i], rgb[3 * i + 1], rgb[3 * i + 2]
            px = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            be[2 * i], be[2 * i + 1] = px >> 8, px & 0xFF
        self.panel.draw_rect((W - w) // 2, row, w, h, bytes(be))
        return None, w, h, 1 << shift

    def png(self) -> bytes:
        buf = io.BytesIO()
        with self._state:
            self.panel.shown.save(buf, "PNG")
        return buf.getvalue()


def _err(code: str, message: str) -> dict:
    return {"ok": False, "error": {"code": code, "message": message}}


def load_source(source: str) -> bytes | None:
    """A local file's bytes, or None for a URL."""
    if source.lower().startswith(("http://", "https://")):
        return None
    return Path(source).expanduser().read_bytes()
