# Testing without a reTerminal

Three levels. Each one runs the firmware's own logic, ported from the pinned SDK
(`firmware/sdk.lock`):
- `esp32/main/image_fetch.c`: download, JPEG scaling, raw RGB565 rows
- `esp32/main/epaper_status.c`: the canvas and the Floyd–Steinberg dither to the six
  Spectra 6 inks
- `esp32/main/noise_control.cpp`: the command descriptions Muse sees

A test compiles the firmware's `dither_color()` and checks the Python port against it pixel
for pixel.

| Level | Needs | Tests |
|---|---|---|
| 1. `simulate`: one image → panel PNG | nothing | your images and the server output |
| 2. `emulate`: virtual reTerminal with a live view | nothing | the HTTP flow, `display.draw_url` errors, refresh behaviour |
| 3. Real Muse → virtual reTerminal | Linux machine with Bluetooth LE, SDK token, Muse app | pairing, the skill, the 7 am schedule, Muse's own image choices |

Set up first: `cd briefing && python3 -m venv .venv && .venv/bin/pip install -e .`

## 1. What would the panel show?

```sh
.venv/bin/muse-briefing demo --out out
.venv/bin/muse-briefing simulate out/briefing.rgb565 --out panel.png          # firmware as written
.venv/bin/muse-briefing simulate out/briefing.rgb565 --out panel.png --fixed  # with the colour fix
.venv/bin/muse-briefing simulate http://192.168.1.20:8765/briefing.rgb565     # from a running server
.venv/bin/muse-briefing simulate photo.jpg --out panel.png                    # any baseline JPEG
```

It prints the same result the device sends back to Muse, e.g.
`{"ok": true, "payload": {"format": "rgb565", "width": 800, ...}}`, or the same error text.

## 2. Virtual reTerminal

```sh
.venv/bin/muse-briefing emulate                 # http://127.0.0.1:8766/
.venv/bin/muse-briefing emulate --fixed --refresh-seconds 30   # behave like the real thing
```

Open the page to watch the panel. It flashes on each refresh and lists recent commands.
Send it commands the way Muse would:

```sh
curl -s localhost:8766/command -H 'Content-Type: application/json' \
  -d '{"command": "display.draw_url", "params": {"url": "http://127.0.0.1:8765/briefing.rgb565"}}'
curl -s localhost:8766/command -d '{"command": "sensors.read"}'
curl -s localhost:8766/command -d '{"command": "display.show_animation"}'
curl -s localhost:8766/capabilities     # the descriptions Muse gets from the real firmware
```

## 3. Real Muse, virtual reTerminal

The SDK's Linux Device SDK is a genuine Muse gadget. `simulator/linux-gadget/prepare.sh`
copies it from the pinned SDK and adds the E1002's `display.draw_url`,
`display.show_animation` and `sensors.read`, with the firmware's exact descriptions. The
commands are forwarded to the virtual reTerminal, so Muse sees a six-colour 800×480 e-paper
display and drives it for real.

```sh
firmware/fetch-sdk.sh
simulator/linux-gadget/prepare.sh       # prints the steps below with full paths
cd briefing && .venv/bin/muse-briefing serve -c briefing.toml &   # the briefing server
.venv/bin/muse-briefing emulate &                                 # the virtual panel
bash ../simulator/linux-gadget/.build/linux/install.sh \
  --from ../simulator/linux-gadget/.build/linux --sdk-token mgst_...
```

Pair `MuseGadgetXXXXXX` in the Muse app (Developer mode). Paste `muse/SKILL.md` into Muse,
then ask it to "show this morning's briefing on the display" and watch
http://127.0.0.1:8766/.

What to know:
- The installer runs the gadget as a system service and gives Muse shell access as the
  account you pick. That is how the Linux SDK works. Use a spare machine or VM with
  Bluetooth passthrough, and read `install.sh` first. Remove it with
  `sudo bash .../install.sh --uninstall`.
- It shows up as `MuseGadgetXXXXXX`, not `MuseGadget-Disp-XXXXXX`. Pairing uses the Linux
  flow (Wi-Fi is already set), not the green button.
- The gadget also keeps the Linux SDK's own commands (`system.run`, `file.*`).
- The virtual device listens on 127.0.0.1. To reach it from another machine, use
  `emulate --host 0.0.0.0` and set `MUSE_RETERMINAL_SIM=http://host:8766` in the gadget
  service's environment.

## What the simulator does *not* cover

- Bluetooth pairing, Wi-Fi joining and the Noise session on the ESP32 itself. Level 3
  covers these only on the Linux SDK's side.
- Memory limits (`out_of_memory`, HTTPS needing more RAM), the panel's real ink appearance,
  ghosting and battery life.
- JPEG decoding uses Pillow, not the ROM's TJpgDec, so JPEG pixels can differ slightly.
  Raw RGB565 is bit-exact.

## The colour byte-order issue it found

Emulating the pinned firmware exposed a bug. `led_status_draw_rect()` `memcpy`s the
high-byte-first RGB565 it receives into the canvas, but `dither_color()` reads the canvas
as native `uint16_t`, which is little-endian on the ESP32-S3. The status screen writes
native values and the black-and-white E1001 path decodes high byte first, so only colour
images are affected. In every image Muse sends, colours come out swapped:

| Sent | Shown (mostly) |
|---|---|
| red | blue |
| blue | green |
| green | red |
| yellow | blue |
| black / white | unchanged |

`muse-briefing simulate` shows this by default. `--fixed` previews the corrected firmware.
`firmware/patches/0001-epaper-colour-image-byte-order.patch` is the 6-line fix: decode high
byte first, as the mono path already does. It is checked by compiling the firmware's code
on a little-endian host, but **not yet on a real E1002**, and it is not applied to the
firmware this repo builds unless you choose to apply it.
