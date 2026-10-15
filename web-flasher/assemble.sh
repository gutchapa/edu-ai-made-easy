#!/usr/bin/env bash
# Assemble the web flasher site from a tokenless reTerminal E1002 build.
#
# Usage: web-flasher/assemble.sh [SITE_DIR]      (default: web-flasher/site)
#
# Needs firmware/fetch-sdk.sh and a build in the SDK's build-reterminal-e1002/
# (CI: tools/board.sh reterminal-e1002 build, with no token). The images are
# copied with their own offsets by the SDK's make_manifest.py, so updates keep
# the device's NVS (pairing, Wi-Fi, SDK token).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/../firmware/common.sh"

SITE="${1:-$HERE/site}"
require_sdk
[ -f "$BUILD_DIR/flasher_args.json" ] || die "no build in $BUILD_DIR; build the firmware first"
if grep -q '^CONFIG_GADGET_SDK_TOKEN="mgst_' "$BUILD_DIR/sdkconfig" 2>/dev/null; then
  die "this build has an SDK token baked in; a public flasher must use a tokenless build"
fi

rm -rf "$SITE"
mkdir -p "$SITE/sdk"
version="$(cat "$ESP32_DIR/version.txt")+${SDK_REF:0:7}"
python3 "$SDK_DIR/web-flasher/make_manifest.py" "$BUILD_DIR" "$SITE/firmware/$BOARD" \
  "Muse Gadget (Seeed reTerminal E1002)" "$version"
cp "$SDK_DIR/web-flasher/"{flasher-hooks.js,paced-serial.js,sdk-token.js} "$SITE/sdk/"
cp "$SDK_DIR/LICENSE" "$SITE/sdk/LICENSE"
cp "$HERE/index.html" "$SITE/"
printf '{"commit": "%s", "sdk_ref": "%s"}\n' \
  "$(git -C "$HERE/.." rev-parse HEAD 2>/dev/null || echo unknown)" "$SDK_REF" > "$SITE/build.json"
info "Site in $SITE"
info "Try it: python3 -m http.server 8000 --bind 127.0.0.1 --directory $SITE  →  http://localhost:8000"
