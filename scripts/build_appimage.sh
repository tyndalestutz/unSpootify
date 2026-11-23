#!/usr/bin/env bash
# Build dist/unSpootify-<version>-x86_64.AppImage (Linux x86_64).
# Steps: fetch sockseek + pinned AppImage tools -> PyInstaller onedir -> prune Qt -> AppDir -> appimagetool.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)"
UV="${UV:-uv}"

TOOLS="$ROOT/vendor/tools"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage"
APPIMAGETOOL_SHA="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
RUNTIME_URL="https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64"
RUNTIME_SHA="2fca8b443c92510f1483a883f60061ad09b46b978b2631c807cd873a47ec260d"

fetch() {  # url sha dest
  if [[ -f "$3" ]] && echo "$2  $3" | sha256sum -c --quiet 2>/dev/null; then return; fi
  mkdir -p "$(dirname "$3")"
  curl -fsSL -o "$3" "$1"
  echo "$2  $3" | sha256sum -c --quiet || { echo "checksum mismatch for $3" >&2; exit 1; }
}
fetch "$APPIMAGETOOL_URL" "$APPIMAGETOOL_SHA" "$TOOLS/appimagetool-x86_64.AppImage"
fetch "$RUNTIME_URL" "$RUNTIME_SHA" "$TOOLS/runtime-x86_64"
chmod +x "$TOOLS/appimagetool-x86_64.AppImage"
scripts/fetch_sockseek.sh linux-x64

"$UV" run pyinstaller packaging/unspootify.spec --noconfirm --distpath dist --workpath build
"$UV" run python scripts/prune_qt.py dist/unspootify

APPDIR="build/unSpootify.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -a dist/unspootify "$APPDIR/usr/lib/unspootify"
cp packaging/unspootify.desktop "$APPDIR/unspootify.desktop"
cp packaging/unspootify.desktop "$APPDIR/usr/share/applications/"
cp assets/icon/png/unspootify-256.png "$APPDIR/unspootify.png"
cp assets/icon/png/unspootify-256.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/unspootify.png"
cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/unspootify/unspootify" "$@"
RUN
chmod +x "$APPDIR/AppRun"

OUT="dist/unSpootify-$VERSION-x86_64.AppImage"
# --appimage-extract-and-run lets this work in containers without FUSE
ARCH=x86_64 "$TOOLS/appimagetool-x86_64.AppImage" --appimage-extract-and-run \
  --runtime-file "$TOOLS/runtime-x86_64" --comp zstd "$APPDIR" "$OUT" >/dev/null
echo "Built $OUT ($(du -h "$OUT" | cut -f1))"
