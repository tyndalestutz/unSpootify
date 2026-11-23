#!/usr/bin/env bash
# Build dist/unSpootify-<version>-<arch>.dmg on macOS (arch = arm64 or x86_64, from this machine).
# Steps: fetch sockseek -> icon (.icns) -> PyInstaller .app -> ad-hoc sign inside out -> verify -> dmg.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' src/unspootify/__init__.py)"
ARCH="$(uname -m)"   # arm64 | x86_64
KEY=$([[ "$ARCH" == arm64 ]] && echo osx-arm64 || echo osx-x64)
UV="${UV:-uv}"

scripts/fetch_sockseek.sh "$KEY"

# .icns from the icon PNGs
ICONSET="build/unspootify.iconset"
rm -rf "$ICONSET" && mkdir -p "$ICONSET"
for s in 16 32 128 256 512; do
  cp "assets/icon/png/unspootify-$s.png" "$ICONSET/icon_${s}x${s}.png"
  d=$((s * 2)); [[ -f "assets/icon/png/unspootify-$d.png" ]] && cp "assets/icon/png/unspootify-$d.png" "$ICONSET/icon_${s}x${s}@2x.png"
done
iconutil -c icns "$ICONSET" -o assets/icon/unspootify.icns

"$UV" run pyinstaller packaging/unspootify.spec --noconfirm --distpath dist --workpath build
APP="dist/unSpootify.app"

# Ad-hoc signature, inside out: the bundled sockseek first, then the whole app (last step, nothing
# may change inside the bundle afterwards or macOS reports it as "damaged").
find "$APP/Contents" -type f \( -name "*.dylib" -o -name "*.so" -o -name sockseek \) -exec codesign --force --sign - {} \;
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"

STAGE="build/dmg"
rm -rf "$STAGE" && mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp "packaging/Open me first.txt" "$STAGE/"
OUT="dist/unSpootify-$VERSION-$ARCH.dmg"
rm -f "$OUT"
hdiutil create -volname "unSpootify" -srcfolder "$STAGE" -ov -format UDZO "$OUT" >/dev/null
echo "Built $OUT ($(du -h "$OUT" | cut -f1))"
