"""muse-briefing: render, preview and serve the reTerminal morning briefing."""

from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
from pathlib import Path

from PIL import Image

from . import config
from .model import Briefing
from .render import HEIGHT, WIDTH, render, to_rgb565
from .sample import sample


def _write(b: Briefing, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    im = render(b)
    im.save(out / "briefing.png")
    (out / "briefing.rgb565").write_bytes(to_rgb565(im))
    print(f"wrote {out / 'briefing.png'} and {out / 'briefing.rgb565'}")


def _lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))  # no packet is sent; picks the outbound interface
            return s.getsockname()[0]
    except OSError:
        return "THIS-COMPUTER-IP"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="muse-briefing", description=__doc__)
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("demo", help="render the built-in sample briefing (no network)")
    d.add_argument("--out", type=Path, default=Path("out"))

    r = sub.add_parser("render", help="collect from your sources (or a JSON file) and render once")
    r.add_argument("-c", "--config", default="briefing.toml")
    r.add_argument("--json", type=Path, help="render this briefing JSON instead of collecting")
    r.add_argument("--out", type=Path, default=Path("out"))

    s = sub.add_parser("serve", help="serve the briefing to the reTerminal over HTTP")
    s.add_argument("-c", "--config", default="briefing.toml")
    s.add_argument("--port", type=int)

    x = sub.add_parser("decode", help="turn a .rgb565 file back into a PNG, to check it")
    x.add_argument("rgb565", type=Path)
    x.add_argument("png", type=Path)

    a = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if a.cmd == "demo":
        _write(sample(), a.out)
    elif a.cmd == "render":
        if a.json:
            b = Briefing.from_json(json.loads(a.json.read_text(encoding="utf-8")))
        else:
            from .sources import collect
            b = collect(config.load(a.config))
        _write(b, a.out)
    elif a.cmd == "serve":
        from .server import serve
        cfg = config.load(a.config)
        if a.port:
            cfg.port = a.port
        print(f"Device URL for display.draw_url: http://{_lan_ip()}:{cfg.port}/briefing.rgb565")
        serve(cfg)
    elif a.cmd == "decode":
        data = a.rgb565.read_bytes()
        if len(data) != WIDTH * HEIGHT * 2:
            print(f"expected {WIDTH * HEIGHT * 2} bytes, got {len(data)}", file=sys.stderr)
            return 1
        rgb = bytearray()
        for i in range(0, len(data), 2):
            v = data[i] << 8 | data[i + 1]
            r, g, b5 = v >> 11, (v >> 5) & 0x3F, v & 0x1F
            rgb += bytes((r << 3 | r >> 2, g << 2 | g >> 4, b5 << 3 | b5 >> 2))
        Image.frombytes("RGB", (WIDTH, HEIGHT), bytes(rgb)).save(a.png)
        print(f"wrote {a.png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
