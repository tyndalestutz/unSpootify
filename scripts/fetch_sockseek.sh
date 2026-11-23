#!/usr/bin/env bash
# Download the pinned sockseek (formerly sldl) binary into vendor/sockseek/<platform>/.
# Usage: scripts/fetch_sockseek.sh [linux-x64|osx-arm64|osx-x64]   (default: this machine)
set -euo pipefail

VERSION="3.0.6"
sha_for() {  # plain case statement: macOS ships bash 3.2 (no associative arrays)
  case "$1" in
    linux-x64) echo 91d7d14fa1293afe94ccb0299e0103f8477a558223f62f4027f5712e4bbf521a ;;
    osx-arm64) echo b7b9602b3ea0d8724b2a4dd1370c97f2f1f7175f901e7088dad714352c4926d9 ;;
    osx-x64) echo 6211374e1fca1f0b0bb4bfc6395e493c5969416e116a976f87bac4bdb99320fd ;;
    *) echo "Unknown platform: $1" >&2; exit 1 ;;
  esac
}

detect() {
  case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) echo linux-x64 ;;
    Darwin-arm64) echo osx-arm64 ;;
    Darwin-x86_64) echo osx-x64 ;;
    *) echo "Unsupported platform: $(uname -s) $(uname -m)" >&2; exit 1 ;;
  esac
}

PLATFORM="${1:-$(detect)}"
EXPECTED="$(sha_for "$PLATFORM")"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/vendor/sockseek/$PLATFORM"
ARCHIVE="sockseek_${VERSION}_${PLATFORM}.tar.gz"
URL="https://github.com/fiso64/sockseek/releases/download/v${VERSION}/${ARCHIVE}"

if [[ -x "$DEST/sockseek" ]] && [[ "$(cat "$DEST/VERSION" 2>/dev/null)" == "$VERSION" ]]; then
  echo "sockseek $VERSION ($PLATFORM) already present."
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "Downloading $URL"
curl -fL --progress-bar -o "$TMP/$ARCHIVE" "$URL"

ACTUAL="$( (sha256sum "$TMP/$ARCHIVE" 2>/dev/null || shasum -a 256 "$TMP/$ARCHIVE") | cut -d' ' -f1)"
if [[ "$ACTUAL" != "$EXPECTED" ]]; then
  echo "Checksum mismatch for $ARCHIVE (got $ACTUAL)" >&2
  exit 1
fi

rm -rf "$DEST" && mkdir -p "$DEST"
tar xzf "$TMP/$ARCHIVE" -C "$DEST"
chmod +x "$DEST/sockseek"
echo "$VERSION" > "$DEST/VERSION"
echo "Installed sockseek $VERSION to $DEST"
