#!/usr/bin/env bash
# Install ESP-IDF (the version in sdk.lock) for the ESP32-S3, the reTerminal
# E1002's chip. The SDK supports no other IDF version.
#
# Usage: firmware/setup-idf.sh
#   IDF_PATH=/somewhere firmware/setup-idf.sh   to install elsewhere
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

if [ -f "$IDF_DIR/export.sh" ]; then
  have="$(git -C "$IDF_DIR" describe --tags --exact-match 2>/dev/null || echo unknown)"
  [ "$have" = "$IDF_VERSION" ] || die "$IDF_DIR holds ESP-IDF $have, need $IDF_VERSION"
  info "ESP-IDF $IDF_VERSION already at $IDF_DIR"
else
  info "Cloning ESP-IDF $IDF_VERSION into $IDF_DIR (a few minutes)"
  mkdir -p "$(dirname "$IDF_DIR")"
  git clone --depth 1 --branch "$IDF_VERSION" --recursive --shallow-submodules \
    https://github.com/espressif/esp-idf.git "$IDF_DIR"
fi

info "Installing the esp32s3 toolchain"
"$IDF_DIR/install.sh" esp32s3

cat <<EOF

Done. The build scripts activate ESP-IDF on their own. For a shell with
idf.py on PATH:

  . "$IDF_DIR/export.sh"
EOF
