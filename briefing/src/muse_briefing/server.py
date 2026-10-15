"""A small LAN server the reTerminal pulls its picture from.

    GET    /briefing.rgb565   the picture as display.draw_url wants it
    GET    /briefing.png      the same picture, for people
    GET    /briefing.json     the data behind it
    POST   /briefing          Muse (or anything) pushes today's briefing as JSON
    DELETE /briefing          drop the pushed briefing, back to built-in sources
    GET    /healthz

A pushed briefing wins for its own day; otherwise the configured sources are
collected, cached for cache_minutes. Plain HTTP on purpose: the device needs
much more free memory for an HTTPS download.
"""

from __future__ import annotations

import hmac
import io
import json
import logging
import threading
import time
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlsplit

from .config import Config
from .model import Briefing
from .render import render, to_rgb565
from .sources import collect

log = logging.getLogger(__name__)

MAX_BODY = 64 * 1024


class State:
    def __init__(self, cfg: Config, collector: Callable[[Config], Briefing] = collect,
                 clock: Callable[[], datetime] | None = None):
        self.cfg = cfg
        self.collector = collector
        self.clock = clock or (lambda: datetime.now(cfg.tz))
        self.lock = threading.Lock()
        self.pushed: Briefing | None = None
        self._cache: tuple[float, Briefing, bytes, bytes] | None = None

    def push(self, b: Briefing) -> None:
        with self.lock:
            self.pushed = b
            self._cache = None

    def clear(self) -> None:
        with self.lock:
            self.pushed = None
            self._cache = None

    def get(self, refresh: bool = False) -> tuple[Briefing, bytes, bytes]:
        """(briefing, rgb565, png), rendered at most once per cache window."""
        with self.lock:
            now = self.clock()
            if self._cache and not refresh:
                ts, b, raw, png = self._cache
                fresh = time.monotonic() - ts < self.cfg.cache_minutes * 60
                if fresh and b.day == now.date():
                    return b, raw, png
            if self.pushed and self.pushed.day == now.date():
                b = self.pushed
            else:
                b = self.collector(self.cfg)
            im = render(b)
            buf = io.BytesIO()
            im.save(buf, "PNG", optimize=True)
            self._cache = (time.monotonic(), b, to_rgb565(im), buf.getvalue())
            return self._cache[1:]


def make_handler(state: State) -> type[BaseHTTPRequestHandler]:
    cfg = state.cfg

    class Handler(BaseHTTPRequestHandler):
        server_version = "muse-briefing"

        def log_message(self, fmt: str, *args) -> None:  # noqa: D401
            log.info("%s %s", self.address_string(), fmt % args)

        def _send(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status: int, obj: object) -> None:
            self._send(status, json.dumps(obj, ensure_ascii=False).encode(), "application/json")

        def _authorized(self) -> bool:
            if not cfg.push_token:
                return True
            got = self.headers.get("Authorization", "")
            return hmac.compare_digest(got.encode(), f"Bearer {cfg.push_token}".encode())

        def _base_url(self) -> str:
            return f"http://{self.headers.get('Host') or f'{cfg.host}:{cfg.port}'}"

        def do_HEAD(self) -> None:
            self.do_GET()

        def do_GET(self) -> None:
            url = urlsplit(self.path)
            refresh = parse_qs(url.query).get("refresh", ["0"])[0] in ("1", "true")
            try:
                if url.path == "/healthz":
                    return self._json(200, {"ok": True})
                if url.path == "/briefing.rgb565":
                    _, raw, _ = state.get(refresh)
                    return self._send(200, raw, "application/octet-stream")
                if url.path == "/briefing.png":
                    _, _, png = state.get(refresh)
                    return self._send(200, png, "image/png")
                if url.path == "/briefing.json":
                    b, _, _ = state.get(refresh)
                    return self._json(200, {"source": "pushed" if b is state.pushed else "sources",
                                            "briefing": b.to_json()})
                if url.path == "/":
                    return self._send(200, _index(self._base_url()).encode(), "text/html; charset=utf-8")
            except Exception:
                log.exception("render failed")
                return self._json(500, {"ok": False, "error": "render failed; see server log"})
            self._json(404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/briefing":
                return self._json(404, {"ok": False, "error": "not found"})
            if not self._authorized():
                return self._json(401, {"ok": False, "error": "bad or missing bearer token"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                n = -1
            if n <= 0 or n > MAX_BODY:
                return self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE if n > MAX_BODY else 400,
                                  {"ok": False, "error": f"send a JSON body up to {MAX_BODY} bytes"})
            try:
                b = Briefing.from_json(json.loads(self.rfile.read(n)))
            except (ValueError, json.JSONDecodeError) as e:
                return self._json(400, {"ok": False, "error": str(e)})
            state.push(b)
            self._json(200, {"ok": True, "draw_url": f"{self._base_url()}/briefing.rgb565"})

        def do_DELETE(self) -> None:
            if urlsplit(self.path).path != "/briefing":
                return self._json(404, {"ok": False, "error": "not found"})
            if not self._authorized():
                return self._json(401, {"ok": False, "error": "bad or missing bearer token"})
            state.clear()
            self._json(200, {"ok": True})

    return Handler


def _index(base: str) -> str:
    return f"""<!doctype html><meta charset="utf-8"><title>Morning briefing</title>
<style>body{{font:16px system-ui;margin:24px;max-width:840px}}img{{border:1px solid #888;max-width:100%}}
code{{background:#eee;padding:2px 4px}}</style>
<h1>Morning briefing</h1>
<p><img src="/briefing.png" width="800" height="480" alt="Current briefing"></p>
<p>Muse draws it with <code>display.draw_url</code> and
<code>{{"url": "{base}/briefing.rgb565"}}</code>.</p>
<p><a href="/briefing.png?refresh=1">Refresh now</a> · <a href="/briefing.json">Data</a></p>
"""


def serve(cfg: Config, state: State | None = None) -> None:
    state = state or State(cfg)
    httpd = ThreadingHTTPServer((cfg.host, cfg.port), make_handler(state))
    log.info("serving on http://%s:%d (device URL: /briefing.rgb565)", cfg.host, cfg.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
