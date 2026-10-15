#!/usr/bin/env bash
# Flash the built firmware to a reTerminal E1002 over USB-C, then open the
# serial monitor (Ctrl+] to quit).
#
# Usage: firmware/flash.sh [PORT] [--no-monitor]
#
# Without PORT, the SDK picks the only USB serial port it finds
# (/dev/cu.usbserial-* or /dev/cu.wchusbserial* on macOS, /dev/ttyUSB* on Linux).
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

port=""
action=flash-monitor
for arg in "$@"; do
  case "$arg" in
    --no-monitor) action=flash ;;
    -h|--help) sed -n '2,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) port="$arg" ;;
  esac
done

require_sdk
[ -f "$BUILD_DIR/muse-gadget.bin" ] || die "no firmware in $BUILD_DIR; run firmware/build.sh first"
activate_idf

cat <<'EOF'
>> If flashing can't connect: hold BOOT, tap RESET, release BOOT, and re-run.
>> Use a USB-C *data* cable; charge-only cables show no serial port.
EOF

if ! "$ESP32_DIR/tools/board.sh" "$BOARD" "$action" ${port:+"$port"}; then
  echo >&2
  echo "Flash failed. On Linux, a permission error means adding yourself to the" >&2
  echo "dialout (Debian/Ubuntu) or uucp (Arch) group, then logging in again." >&2
  exit 1
fi
