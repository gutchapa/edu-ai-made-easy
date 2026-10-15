# What to buy

## Must have

| Item | Price (approx.) | Notes |
|---|---|---|
| **Seeed Studio reTerminal E1002** | $99–109 | The 7.3" **colour** (Spectra 6) model. The E1001 is the 7.5" black-and-white one; the firmware supports it too, but this repo's briefing is designed for the colour panel. Comes in a metal case with a stand and a 2000 mAh battery. [Seeed Studio](https://www.seeedstudio.com/reTerminal-E1002-p-6533.html), or a local Seeed distributor. |
| **USB-C data cable** | $5–10 | For flashing. Check the box first: if one came with it, use that. Charge-only cables show no serial port, the #1 "it doesn't connect" cause. Use USB-C to USB-C or USB-A to USB-C, whichever fits your computer. |

That's it for the display itself.

## Need, but you probably already have

| Item | Notes |
|---|---|
| Computer with **Chrome or Edge** | For the web flasher (Windows, macOS, Linux or ChromeOS; not phones or Safari/Firefox). On Windows you may need the free WCH CH34x USB driver. |
| Phone with the **Muse app** (iOS/Android) | For pairing. Turn on Developer mode in Settings → Devices. |
| **2.4 GHz Wi-Fi** | ESP32-S3 can't use 5 GHz-only networks. |
| Muse Gadgets **SDK token** | Free from [gadgets.muse.ai](https://gadgets.muse.ai/settings/sdk-tokens). Personal, non-commercial use. |

## For the briefing server: pick one

The server has to run all the time on your home network, because the display downloads its
picture from it each morning.

| Option | Price (approx.) | Notes |
|---|---|---|
| Computer you already leave on (desktop, NAS, home server) | $0 | Needs Python 3.11+. |
| **Raspberry Pi Zero 2 W** + 5 V/2.5 A micro-USB PSU + 16 GB microSD | $15 + $8 + $6 | Cheapest dedicated box. Plenty for this. |
| Raspberry Pi 4 / 5 + official PSU + microSD | $45–80 + $8–12 + $6 | If you want it to run other home services too. |

## Optional

| Item | Why |
|---|---|
| Wall-mount / adhesive hooks | The included stand works on a shelf. The case can also hang on a wall. |
| 5 V USB-C wall charger | Only to top up the battery every few months, or to run it always plugged in. |

**Typical total:** about **$105–115** if you already have an always-on computer, about
**$135–145** with a Raspberry Pi Zero 2 W setup. Prices are approximate (Oct 2026) and
vary by country and shipping.
