"""HTTP front for the virtual reTerminal.

    GET  /              live view of the panel in a browser
    GET  /panel.png     what the panel shows now
    GET  /state         refresh count, mode and the last commands
    GET  /capabilities  the command specs the firmware registers with Muse
    POST /command       {"command": "display.draw_url", "params": {"url": ...}}

The patched Linux gadget (simulator/linux-gadget) forwards Muse's commands
here, so a real Muse can drive the virtual device end to end.
"""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .device import VirtualReTerminal
from .specs import COMMAND_SPECS

log = logging.getLogger(__name__)

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Virtual reTerminal</title>
<style>
:root{--bg:#e9e6df;--text:#1b1d21;--muted:#5f6670;--bezel:#2a2b2e}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141518;--text:#e8eaed;--muted:#9ba1a9;--bezel:#3a3c40}}
body{margin:0;padding:24px 16px;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}
main{max-width:880px;margin:0 auto}
h1{font-size:1.3rem;margin:0 0 4px}
p{margin:0 0 14px;color:var(--muted)}
.frame{background:var(--bezel);padding:18px 18px 28px;border-radius:14px;box-shadow:0 10px 30px rgb(0 0 0/.25)}
.frame img{display:block;width:100%;height:auto;image-rendering:pixelated;background:#fff}
.frame.refreshing img{animation:flash 1.2s steps(2) 3}
@keyframes flash{50%{filter:invert(1)}}
.meta{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px;font-size:.9rem;color:var(--muted)}
pre{background:rgb(0 0 0/.06);padding:10px;border-radius:8px;overflow:auto;font-size:.8rem;max-height:240px}
</style></head><body><main>
<h1>Virtual reTerminal E1002</h1>
<p>Six-ink e-paper, emulated from the Muse Gadget firmware. <span id="mode"></span></p>
<div class="frame" id="frame"><img id="panel" src="panel.png" width="800" height="480" alt="Panel"></div>
<div class="meta"><span id="refreshes"></span><span id="last"></span></div>
<pre id="log"></pre>
<script>
let seen = -1;
async function tick() {
  try {
    const s = await (await fetch("state")).json();
    document.getElementById("mode").textContent = s.fixed
      ? "Mode: fixed byte order (previewing a corrected firmware)."
      : "Mode: firmware as written (pinned SDK).";
    if (s.refreshes !== seen) {
      if (seen >= 0) { const f = document.getElementById("frame"); f.classList.remove("refreshing"); void f.offsetWidth; f.classList.add("refreshing"); }
      seen = s.refreshes;
      document.getElementById("panel").src = "panel.png?" + s.refreshes;
    }
    document.getElementById("refreshes").textContent = `Refreshes: ${s.refreshes}`;
    const last = s.log[s.log.length - 1];
    document.getElementById("last").textContent = last ? `Last: ${last.command} → ${last.result.ok ? "ok" : (last.result.error?.message ?? "error")}` : "";
    document.getElementById("log").textContent = s.log.slice().reverse().map(e => JSON.stringify(e)).join("\\n");
  } catch {}
}
setInterval(tick, 1000); tick();
</script></main></body></html>
"""


def make_handler(dev: VirtualReTerminal) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "virtual-reterminal"

        def log_message(self, fmt: str, *args) -> None:
            log.debug("%s %s", self.address_string(), fmt % args)

        def _send(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, obj: object) -> None:
            self._send(status, json.dumps(obj).encode(), "application/json")

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/":
                return self._send(200, PAGE.encode(), "text/html; charset=utf-8")
            if path == "/panel.png":
                return self._send(200, dev.png(), "image/png")
            if path == "/state":
                return self._json(200, {"fixed": dev.panel.fixed, "refreshes": dev.panel.refreshes,
                                        "image_mode": dev.panel.image_mode, "log": dev.log[-10:]})
            if path == "/capabilities":
                return self._json(200, COMMAND_SPECS)
            self._json(404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/command":
                return self._json(404, {"ok": False, "error": "not found"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(n) if 0 < n <= 64 * 1024 else b"")
                command, params = body["command"], body.get("params") or {}
                if not isinstance(command, str) or not isinstance(params, dict):
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                return self._json(400, {"ok": False, "error": {"code": "bad_request",
                                        "message": 'send {"command": "...", "params": {...}}'}})
            log.info("%s %s", command, json.dumps(params))
            result = dev.run(command, params)
            log.info("→ %s", json.dumps(result))
            self._json(200, result)

    return Handler


def serve(dev: VirtualReTerminal, host: str = "127.0.0.1", port: int = 8766) -> None:
    httpd = ThreadingHTTPServer((host, port), make_handler(dev))
    log.info("virtual reTerminal on http://%s:%d", host, port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
