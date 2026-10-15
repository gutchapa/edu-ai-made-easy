#!/usr/bin/env bash
# Build the Muse gadget firmware for the Seeed reTerminal E1002 with your SDK
# token baked in.
#
# Usage: MUSE_SDK_TOKEN=mgst_... firmware/build.sh
#
# The token comes from MUSE_SDK_TOKEN, else firmware/.sdk-token (git-ignored),
# else a hidden prompt. It lands only in the SDK's build directory, never in
# this repo. Get one at https://gadgets.muse.ai/settings/sdk-tokens.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

require_sdk

token="${MUSE_SDK_TOKEN:-}"
if [ -z "$token" ] && [ -f "$FIRMWARE_DIR/.sdk-token" ]; then
  token="$(tr -d '[:space:]' < "$FIRMWARE_DIR/.sdk-token")"
fi
if [ -z "$token" ] && [ -t 0 ]; then
  read -r -s -p "Muse SDK token (mgst_...): " token
  echo
fi
[ -n "$token" ] || die "no SDK token; set MUSE_SDK_TOKEN or write firmware/.sdk-token"
case "$token" in
  mgst_*) ;;
  *) die "SDK tokens start with mgst_ (got ${token:0:5}...)" ;;
esac
case "$token" in
  *[!A-Za-z0-9_-]*) die "SDK token has unexpected characters" ;;
esac

activate_idf

# Seed or update the token in the board's sdkconfig. ESP-IDF loads the
# sdkconfig.defaults overlays first and this file on top, so a file holding
# only the token still gets every board setting.
mkdir -p "$BUILD_DIR"
cfg="$BUILD_DIR/sdkconfig"
line="CONFIG_GADGET_SDK_TOKEN=\"$token\""
if [ -f "$cfg" ] && grep -q '^CONFIG_GADGET_SDK_TOKEN=' "$cfg"; then
  tmp="$(mktemp)"
  awk -v l="$line" '/^CONFIG_GADGET_SDK_TOKEN=/{print l; next} {print}' "$cfg" > "$tmp"
  mv "$tmp" "$cfg"
else
  echo "$line" >> "$cfg"
fi
chmod 600 "$cfg"

info "Building $BOARD (token ${token:0:9}...)"
"$ESP32_DIR/tools/board.sh" "$BOARD" build

grep -q "^CONFIG_GADGET_SDK_TOKEN=\"$token\"" "$cfg" \
  || die "the build dropped the SDK token from $cfg; set it with idf.py menuconfig"
info "Firmware: $BUILD_DIR/muse-gadget.bin"
info "Next: firmware/flash.sh"
