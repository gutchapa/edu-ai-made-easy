"""Command specs the reTerminal E1002 firmware registers with Muse
(esp32/main/noise_control.cpp at the pinned SDK revision).

Standard library only: simulator/linux-gadget/patch_executor.py embeds this
in the Linux Device SDK, whose environment has no Pillow.
"""

W, H = 800, 480
ROW_BYTES = W * 2

# The capability text the E1002 firmware registers with Muse
# (esp32/main/noise_control.cpp), so Muse treats the virtual device the same.
DRAW_URL_DESCRIPTION = (
    f"Download an image and draw it on the {W}x{H} six-colour e-paper screen (E Ink Spectra 6), "
    "4 bits per pixel. Takes a baseline (not progressive) JPEG, shrunk 1/2, 1/4 or 1/8 on the "
    f"device if needed and centred across, or raw RGB565 (high byte first, {ROW_BYTES} bytes per "
    "row). The screen has only six inks: black #000000, white #ffffff, yellow #ffff00, red "
    "#ff0000, blue #0000ff and green #00ff00, shown exactly. The device dithers every other "
    "colour and gray to dots of these, so photos look grainy and muted, and text, charts and "
    "flat artwork are sharpest drawn in those six colours only. It refreshes once the whole "
    "image is in, taking about 30 s and flashing, so send one whole screen rather than several "
    "parts, at most about once a minute. The image stays on screen without power. Plain "
    "http:// uses the least device memory. Replies when the image is drawn. Hides the status "
    "screen until display.show_animation."
)

COMMAND_SPECS = {
    "display.draw_url": {
        "description": DRAW_URL_DESCRIPTION,
        "required": {"url": {"type": "string", "description": "http:// or https:// URL of the image."}},
        "optional": {"row": {"type": "integer", "description": "Row to draw the top of the image at; default 0."}},
        "timeout_ms": 120000,
    },
    "display.show_animation": {
        "description": "Clear the image and bring back the status screen and the agent's name.",
        "required": {},
        "optional": {},
    },
    "sensors.read": {
        "description": (
            "Read the onboard air sensor: temperature in degrees Celsius and relative humidity in "
            "percent. Each reading has its age in seconds; a sensor with no recent reading is null."
        ),
        "required": {},
        "optional": {},
    },
}
