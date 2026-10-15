import io
import json
import random
import shutil
import subprocess
import threading
import urllib.request
from array import array
from datetime import datetime
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from muse_briefing.config import Config
from muse_briefing.emulator.device import VirtualReTerminal
from muse_briefing.emulator.panel import INK_CODES, W, H, dither_color
from muse_briefing.emulator.server import make_handler as device_handler
from muse_briefing.render import INKS, render, to_rgb565
from muse_briefing.sample import sample
from muse_briefing.server import State, make_handler as briefing_handler

SDK_C = Path(__file__).resolve().parents[2] / "firmware/.sdk/esp32/main/epaper_status.c"
BLACK, WHITE, YELLOW, RED, BLUE, GREEN = INKS


def solid_be(colour565: int, rows: int = H) -> bytes:
    return bytes((colour565 >> 8, colour565 & 0xFF)) * (W * rows)


def shown_colours(dev: VirtualReTerminal) -> dict:
    counts = dev.panel.shown.getcolors(maxcolors=1 << 16)
    total = sum(n for n, _ in counts)
    return {c: n / total for n, c in counts}


def test_fixed_mode_shows_the_briefing_exactly():
    im = render(sample())
    dev = VirtualReTerminal(fixed=True)
    r = dev.draw_bytes(to_rgb565(im))
    assert r["ok"] and r["payload"]["format"] == "rgb565" and r["payload"]["height"] == H
    assert ImageChops.difference(im, dev.panel.shown).getbbox() is None


@pytest.mark.parametrize("sent,shown_as", [
    (0xF800, BLUE), (0x001F, GREEN), (0x07E0, RED), (0xFFE0, BLUE),
])
def test_firmware_as_written_swaps_colour_bytes(sent, shown_as):
    dev = VirtualReTerminal()
    dev.draw_bytes(solid_be(sent))
    colours = shown_colours(dev)
    assert max(colours, key=colours.get) == shown_as


@pytest.mark.parametrize("fixed", [False, True])
def test_black_and_white_survive_either_way(fixed):
    for c565, ink in ((0x0000, BLACK), (0xFFFF, WHITE)):
        dev = VirtualReTerminal(fixed=fixed)
        dev.draw_bytes(solid_be(c565))
        assert shown_colours(dev) == {ink: 1.0}


def test_gray_dithers_to_black_and_white_dots():
    dev = VirtualReTerminal(fixed=True)
    dev.draw_bytes(solid_be(0x8410))  # mid gray
    colours = shown_colours(dev)
    # Almost all black and white; error build-up adds a stray coloured dot or two.
    assert colours[BLACK] + colours[WHITE] > 0.99 and 0.4 < colours[WHITE] < 0.6


def test_raw_errors_match_firmware():
    dev = VirtualReTerminal(fixed=True)
    assert dev.draw_bytes(solid_be(0, 10) + b"\x00")["error"]["message"].startswith("raw data must be whole rows")
    r = dev.draw_bytes(solid_be(0, 100), row=400)
    assert r["error"]["message"] == "image runs past the last row"
    # What fitted is still shown: rows 400..479 black.
    assert dev.panel.shown.getpixel((10, 479)) == BLACK and dev.panel.shown.getpixel((10, 10)) == WHITE


def _jpeg(size, colour=(255, 0, 0), progressive=False) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, "JPEG", quality=95, progressive=progressive)
    return buf.getvalue()


def test_jpeg_is_scaled_by_powers_of_two_and_centred():
    dev = VirtualReTerminal(fixed=True)
    r = dev.draw_bytes(_jpeg((1600, 600)))
    assert r["ok"] and r["payload"]["scale"] == 2 and (r["payload"]["width"], r["payload"]["height"]) == (800, 300)
    r = dev.draw_bytes(_jpeg((400, 200)))
    assert r["payload"]["scale"] == 1
    assert dev.panel.shown.getpixel((400, 100)) == RED  # 200..600 across, drawn from row 0
    assert dev.panel.shown.getpixel((100, 100)) == RED  # earlier image stays: canvas isn't cleared


def test_jpeg_rejections():
    dev = VirtualReTerminal()
    assert "progressive" in dev.draw_bytes(_jpeg((64, 64), progressive=True))["error"]["message"]
    assert dev.draw_bytes(_jpeg((7000, 100)))["error"]["message"] == "JPEG is too large even at 1/8 scale"


def test_commands_and_params():
    dev = VirtualReTerminal()
    assert dev.run("display.draw_url", {})["error"]["code"] == "missing_param"
    assert dev.run("display.draw_url", {"url": "ftp://x"})["error"]["code"] == "invalid_param"
    assert dev.run("sensors.read")["payload"]["temperature"]["unit"] == "C"
    assert dev.run("nope")["ok"] is False
    dev.draw_bytes(solid_be(0))
    assert dev.run("display.show_animation")["ok"] and not dev.panel.image_mode


def _serve(handler):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def test_end_to_end_device_pulls_from_briefing_server():
    day = datetime(2026, 10, 15, 7, 0)
    state = State(Config(), collector=lambda cfg: sample(day.date()), clock=lambda: day)
    b_httpd, b_url = _serve(briefing_handler(state))
    dev = VirtualReTerminal(fixed=True)
    d_httpd, d_url = _serve(device_handler(dev))
    try:
        body = json.dumps({"command": "display.draw_url", "params": {"url": b_url + "/briefing.rgb565"}}).encode()
        req = urllib.request.Request(d_url + "/command", data=body, headers={"Content-Type": "application/json"})
        result = json.load(urllib.request.urlopen(req, timeout=30))
        assert result["ok"], result
        png = urllib.request.urlopen(d_url + "/panel.png", timeout=10).read()
        assert ImageChops.difference(render(sample(day.date())), Image.open(io.BytesIO(png)).convert("RGB")).getbbox() is None
        caps = json.load(urllib.request.urlopen(d_url + "/capabilities", timeout=10))
        assert "Spectra 6" in caps["display.draw_url"]["description"]
    finally:
        for h in (b_httpd, d_httpd):
            h.shutdown()
            h.server_close()


HARNESS = r"""
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
%s
int main(int argc, char **argv) {
    int w = atoi(argv[1]), h = atoi(argv[2]);
    uint16_t *rgb = malloc(w * h * 2);
    if (fread(rgb, 2, w * h, stdin) != (size_t)(w * h)) return 1;
    uint8_t *codes = malloc(w * h / 2);
    int16_t *err = malloc(6 * (w + 2) * sizeof(int16_t));
    dither_color(rgb, codes, w, h, err);
    fwrite(codes, 1, w * h / 2, stdout);
    return 0;
}
"""


@pytest.mark.skipif(not SDK_C.exists() or not shutil.which("cc"),
                    reason="needs firmware/fetch-sdk.sh and a C compiler")
def test_python_dither_matches_the_firmware_c(tmp_path):
    src = SDK_C.read_text()
    start = src.index("// The Spectra 6 inks")
    end = src.index("// ---- Panel state")
    (tmp_path / "h.c").write_text(HARNESS % src[start:end])
    exe = tmp_path / "h"
    subprocess.run(["cc", "-O1", "-o", str(exe), str(tmp_path / "h.c")], check=True)

    w, h = 64, 48
    rnd = random.Random(1234)
    canvas = array("H", (rnd.randrange(65536) for _ in range(w * h)))
    out = subprocess.run([str(exe), str(w), str(h)], input=canvas.tobytes(),
                         capture_output=True, check=True).stdout
    c_codes = [b for byte in out for b in (byte >> 4, byte & 0xF)]
    py_codes = [INK_CODES[i] for i in dither_color(canvas, w, h)]
    assert py_codes == c_codes
