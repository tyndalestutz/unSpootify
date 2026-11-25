#!/usr/bin/env bash
# CI check on a Mac runner, using the app *as a user gets it*: copied out of the mounted dmg with the
# "downloaded from the internet" flag set. Usage: packaging/test/macos_check.sh dist/unSpootify-*.dmg
set -euo pipefail
DMG="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"
MNT="$WORK/mnt"; mkdir -p "$MNT"
hdiutil attach -nobrowse -readonly -mountpoint "$MNT" "$DMG" >/dev/null
trap 'hdiutil detach "$MNT" -quiet || true' EXIT
test -f "$MNT/Open me first.txt" && test -L "$MNT/Applications"
cp -R "$MNT/unSpootify.app" "$WORK/"
APP="$WORK/unSpootify.app"
xattr -w com.apple.quarantine "0081;$(printf %x "$(date +%s)");Safari;" "$APP"
xattr -w com.apple.quarantine "0081;$(printf %x "$(date +%s)");Safari;" "$APP/Contents/Frameworks/vendor/sockseek/"*/sockseek 2>/dev/null || true

echo "== signature"
codesign --verify --deep --strict "$APP"
EXE="$APP/Contents/MacOS/unspootify"
plutil -p "$APP/Contents/Info.plist" | grep -E "CFBundleShortVersionString|CFBundleIdentifier"

echo "== offline download through the packaged app (finalize callback per song)"
SHARE="$WORK/share"
uv run python "$ROOT/scripts/make_mock_library.py" "$ROOT/tests/fixtures/road_trip.csv" "$SHARE" --missing 8 --flac 4 --flac-only 6 >/dev/null
start=$(date +%s)
"$EXE" run "$ROOT/tests/fixtures/road_trip.csv" --home "$WORK/home" --library "$WORK/lib" --mock-dir "$SHARE" > "$WORK/run.jsonl"
echo "took $(( $(date +%s) - start ))s for 8 songs"
grep -o '"downloaded": [0-9]*, "skipped": [0-9]*, "failed": [0-9]*' "$WORK/run.jsonl"
grep -q '"downloaded": 7' "$WORK/run.jsonl"
test -f "$WORK/lib/The Killers/Hot Fuss [MP3]/Mr. Brightside.mp3"
! pgrep -f "vendor/sockseek" >/dev/null || { echo "sockseek still running"; exit 1; }

echo "== experimental FLAC -> MP3 with the bundled encoder (no ffmpeg needed)"
"$EXE" run "$ROOT/tests/fixtures/road_trip.csv" --home "$WORK/home2" --library "$WORK/lib2" --mock-dir "$SHARE" --convert-mp3 -v > "$WORK/run2.jsonl"
grep '"MP3:"' "$WORK/run2.jsonl" || true
test -f "$WORK/lib2/OutKast/Speakerboxxx-The Love Below [MP3]/Hey Ya!.mp3"
test -z "$(find "$WORK/lib2" -name '*.flac')"

echo "== window opens (Cocoa/WebKit)"
UNSPOOTIFY_HOME="$WORK/gui" "$EXE" --smoke-test | tee "$WORK/smoke.txt"
grep -q "SMOKE ok" "$WORK/smoke.txt"
! pgrep -f "vendor/sockseek" >/dev/null
echo "macOS check passed"
