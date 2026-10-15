---
name: gadget-reterminal-morning-briefing
description: >-
  Show the family morning briefing (calendar, top to-dos, weather) on a paired Seeed
  reTerminal E1002 e-ink Muse gadget, every morning at 7:00, using the muse-briefing server
  on the home network. Use when asked to show, refresh or schedule the briefing on the
  living-room e-ink display.
---

# Morning Briefing on the reTerminal E1002

The living-room display is a Muse gadget advertising as `MuseGadget-Disp-XXXXXX`: a 7.3"
800×480 six-colour e-ink panel (black, white, yellow, red, blue, green). A small server on
the home network, `muse-briefing`, renders the briefing in exactly those six inks and
serves it. The gadget downloads and draws it.

Replace these before use:

- `BRIEFING_URL`: the server's address, e.g. `http://192.168.1.20:8765`. Running
  `muse-briefing serve` prints it.
- `PUSH_TOKEN`: the server's `push_token`, only if one is set.

## Workflow

1. **Gather today's briefing** in the household's timezone:
   - Calendar: today's events from the family calendars, all-day first, then by start time.
     At most 7. Use 24-hour `HH:MM` times and short titles.
   - To-dos: the top 5 open to-dos, most important first, each under ~40 characters.
   - Weather: a short summary ("Light rain"), today's high and low, the current temperature
     and the chance of rain in percent.
   - Optional `note`: one line worth shouting about ("Library books due back Friday").

2. **Push it** with `POST BRIEFING_URL/briefing`, `Content-Type: application/json` and, if
   set, `Authorization: Bearer PUSH_TOKEN`:

   ```json
   {
     "day": "2026-10-15",
     "title": "Good morning, Chapa family",
     "events": [{"time": "", "title": "Diwali holidays begin"},
                {"time": "07:45", "title": "School run", "location": "Greenwood Primary"}],
     "todos": ["Pay electricity bill", "Call grandma"],
     "weather": {"summary": "Light rain", "icon": "rain", "now": 18, "high": 24, "low": 16,
                 "precip": 70, "units": "C"},
     "note": "Library books due back Friday",
     "updated": "07:00"
   }
   ```

   `icon` is one of `sun`, `partly`, `cloud`, `fog`, `rain`, `snow`, `storm`. Leave it out
   and the server picks one from the summary. The reply is `{"ok": true, "draw_url": ...}`.
   If the push fails (the server is unreachable from Muse, or replies 4xx), go straight to
   step 3. The server then draws from its own configured calendar, to-do file and weather.

3. **Draw it** by sending the gadget `display.draw_url` with
   `{"url": "BRIEFING_URL/briefing.rgb565"}`. Use the raw RGB565 URL, not the PNG or a JPEG:
   it is pre-quantized to the panel's inks, so the gadget's dithering leaves it crisp. The
   gadget fetches the URL itself over the home Wi-Fi.

4. **Schedule**: repeat steps 1 to 3 every day at 07:00 local time.

## Verify the Result

- `display.draw_url` answers asynchronously. Success is `ok: true` with
  `format: "rgb565"`, `width: 800`, `height: 480`. Report any `error.code` and `message`
  (e.g. `out_of_memory`, `invalid_image`, `server answered HTTP 500`) instead of retrying in
  a loop.
- A refresh takes about 30 seconds and the panel flashes while it redraws. That is normal.

## Limits

- Do not redraw more often than needed. Each refresh is slow and costs battery. Morning plus
  on-request refreshes is plenty.
- Use `http://` on the LAN. HTTPS downloads need memory the gadget may not have free.
- The gadget's SHT4x sensor (`sensors.read`) gives the room temperature and humidity. Add
  them to `note` if the family asks.
- The SDK token is personal and non-commercial: never share it, and never sell or publicly
  list the device while it holds the token.

## Sources

- [Muse Gadget SDK](https://github.com/facebookincubator/muse-gadget-sdk): `esp32/main/app.c`
  (`display.draw_url`), `esp32/main/image_fetch.h` (accepted formats),
  `esp32/devices/README.md` (reTerminal E1002)
