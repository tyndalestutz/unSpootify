#!/usr/bin/env bash
# Clean-machine test: a fresh Ubuntu container with only a desktop-ish baseline (X server, fonts,
# GL) runs the AppImage: launch check + offline download through the packaged app.
# Usage: packaging/test/clean_linux.sh dist/unSpootify-<v>-x86_64.AppImage <mock-share-dir> [ubuntu:24.04]
set -euo pipefail
APPIMAGE="$(readlink -f "$1")"; SHARE="$(readlink -f "$2")"; IMAGE="${3:-ubuntu:24.04}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
docker run --rm -v "$APPIMAGE:/app/unSpootify.AppImage:ro" -v "$SHARE:/share:ro" \
  -v "$ROOT/tests/fixtures:/fixtures:ro" "$IMAGE" bash -euc '
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >/dev/null
  # a typical desktop baseline: X/GL, GTK (pulls GLib, fonts, cairo, pango), NSS, sound, D-Bus
  PKGS="xvfb xauth fonts-dejavu-core libgl1 libegl1 libgbm1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 \
    libxcb-keysyms1 libxcb-shape0 libxcb-xinerama0 libxcb-render-util0 libxcb-image0 libnss3 libdbus-1-3"
  apt-get install -y -qq $PKGS libgtk-3-0t64 libasound2t64 >/dev/null 2>&1 || apt-get install -y -qq $PKGS libgtk-3-0 libasound2 >/dev/null
  useradd -m friend && cd /home/friend
  su friend -c "
    export APPIMAGE_EXTRACT_AND_RUN=1 HOME=/home/friend
    timeout 120 xvfb-run -a /app/unSpootify.AppImage --smoke-test 2>&1 | grep -E \"SMOKE|rror\" | head -5
    timeout 200 /app/unSpootify.AppImage run /fixtures/road_trip.csv --mock-dir /share --library /home/friend/Music/unSpootify \
      | grep -oE \"\\\"downloaded\\\": [0-9]+, \\\"skipped\\\": [0-9]+, \\\"failed\\\": [0-9]+\"
    find /home/friend/Music/unSpootify -type f | sort | sed s,/home/friend/,,
  "'
