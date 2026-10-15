from datetime import date

from muse_briefing.model import Briefing, Event, Weather
from muse_briefing.render import HEIGHT, INKS, WIDTH, render, to_rgb565
from muse_briefing.sample import sample


def expand565(hi: int, lo: int) -> tuple[int, int, int]:
    """What the firmware does with each RGB565 pixel before dithering."""
    v = hi << 8 | lo
    r, g, b = v >> 11, (v >> 5) & 0x3F, v & 0x1F
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


def nearest_ink(r: int, g: int, b: int) -> int:
    """Port of nearest_ink() in the SDK's esp32/main/epaper_status.c."""
    y = (77 * r + 150 * g + 29 * b) >> 8
    best, best_d = 0, 0
    for i, (ir, ig, ib) in enumerate(INKS):
        iy = (77 * ir + 150 * ig + 29 * ib) >> 8
        dy, du, dv = y - iy, (r - y) - (ir - iy), (b - y) - (ib - iy)
        d = dy * dy + du * du + dv * dv
        if i == 0 or d < best_d:
            best, best_d = i, d
    return best


def test_size_and_only_inks():
    im = render(sample())
    assert im.size == (WIDTH, HEIGHT)
    colours = {c for _, c in im.getcolors(maxcolors=1 << 16)}
    assert colours <= set(INKS)
    assert len(colours) == 6  # the sample uses every ink


def test_rgb565_survives_the_device_dither_unchanged():
    raw = to_rgb565(render(sample()))
    assert len(raw) == WIDTH * HEIGHT * 2
    seen = {(raw[i], raw[i + 1]) for i in range(0, len(raw), 2)}
    for hi, lo in seen:
        c = expand565(hi, lo)
        # Each pixel decodes to an exact ink and is its own nearest ink, so
        # Floyd-Steinberg on the device carries zero error and changes nothing.
        assert c in INKS
        assert INKS[nearest_ink(*c)] == c


def test_rgb565_is_big_endian():
    raw = to_rgb565(render(sample()))
    assert raw[:2] == bytes((0x00, 0x1F))  # top-left is the blue header


def test_empty_and_overlong_briefings_render():
    render(Briefing(day=date(2026, 1, 1)))
    long = "x" * 500
    b = Briefing(day=date(2026, 1, 1), title=long, note=long,
                 events=[Event("10:00", long, long)] * 30, todos=[long] * 30,
                 weather=Weather(summary=long, icon="storm", now=-12.4, high=None, low=-20, precip=100))
    assert render(b).size == (WIDTH, HEIGHT)


def test_every_icon_draws():
    for icon in ("sun", "partly", "cloud", "fog", "rain", "snow", "storm"):
        b = Briefing(day=date(2026, 1, 1), weather=Weather(summary="x", icon=icon))
        render(b)
