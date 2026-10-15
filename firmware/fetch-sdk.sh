#!/usr/bin/env bash
# Fetch the Muse Gadget SDK at the revision pinned in sdk.lock into
# firmware/.sdk (git-ignored). Safe to re-run: it moves an existing checkout
# to the pinned revision.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

if [ ! -d "$SDK_DIR/.git" ]; then
  info "Cloning $SDK_REPO into $SDK_DIR"
  git init -q "$SDK_DIR"
  git -C "$SDK_DIR" remote add origin "$SDK_REPO"
fi

info "Checking out $SDK_REF"
git -C "$SDK_DIR" fetch -q --depth 1 origin "$SDK_REF"
git -C "$SDK_DIR" checkout -q --detach FETCH_HEAD
info "SDK ready: $(git -C "$SDK_DIR" rev-parse --short HEAD)"
