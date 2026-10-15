#!/usr/bin/env bash
# Build a Linux Device SDK checkout that poses as a reTerminal E1002, for
# testing with a real Muse and no reTerminal.
#
# Usage: simulator/linux-gadget/prepare.sh
#
# Copies the SDK's linux/ (pinned in firmware/sdk.lock) to
# simulator/linux-gadget/.build/linux, adds the E1002's display commands, and
# prints the install command. Install on a Linux machine with Bluetooth LE
# (a laptop or a Raspberry Pi), the same one that runs `muse-briefing emulate`.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/../../firmware/common.sh"

require_sdk
OUT="$HERE/.build/linux"
rm -rf "$OUT"
mkdir -p "$(dirname "$OUT")"
cp -R "$SDK_DIR/linux" "$OUT"
python3 "$HERE/patch_executor.py" "$OUT"

cat <<EOF

Ready: $OUT

1. Start the virtual reTerminal (keep it running):
     cd briefing && .venv/bin/muse-briefing emulate      # add --fixed to preview the colour fix
   and open http://127.0.0.1:8766/ to watch the panel.
2. Install the gadget service (needs sudo and Bluetooth LE; read install.sh first):
     bash "$OUT/install.sh" --from "$OUT" --sdk-token mgst_...
3. Pair it in the Muse app (Settings > Devices > Developer mode > Add Device,
   "MuseGadgetXXXXXX"), then paste muse/SKILL.md into Muse and ask it to
   show the briefing on the display.

Remove later with: sudo bash "$OUT/install.sh" --uninstall
EOF
