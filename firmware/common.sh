# Shared helpers for the firmware scripts. Source, don't run.
# shellcheck shell=bash
# Variables here are used by the scripts that source this file.
# shellcheck disable=SC2034

FIRMWARE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$FIRMWARE_DIR/sdk.lock"

SDK_DIR="${MUSE_SDK_DIR:-$FIRMWARE_DIR/.sdk}"
ESP32_DIR="$SDK_DIR/esp32"
BUILD_DIR="$ESP32_DIR/build-$BOARD"
IDF_DIR="${IDF_PATH:-$HOME/esp/esp-idf-$IDF_VERSION}"

die() { echo "error: $*" >&2; exit 1; }
info() { echo ">> $*"; }

require_sdk() {
  [ -x "$ESP32_DIR/tools/board.sh" ] || die "SDK not found at $SDK_DIR; run firmware/fetch-sdk.sh first"
}

# Put idf.py on PATH, the same way the SDK's board.sh looks for it.
activate_idf() {
  command -v idf.py >/dev/null 2>&1 && return 0
  local d
  for d in "${IDF_PATH:-}" "$HOME/esp/esp-idf-$IDF_VERSION" "$HOME/esp/esp-idf-v6" "$HOME/esp/esp-idf"; do
    if [ -n "$d" ] && [ -f "$d/export.sh" ]; then
      # shellcheck disable=SC1091
      . "$d/export.sh" >/dev/null 2>&1
      break
    fi
  done
  command -v idf.py >/dev/null 2>&1 || die "idf.py not found; run firmware/setup-idf.sh first"
}
