# unSpootify rework plan

> The plan of record. Work happens one phase at a time, in order. New ideas go to
> **Backlog**, not into the current phase. Tick boxes as items land; update the
> **Status** line at the end of every working session.

**Status:** Phase 1 final UI test (2026-11-23): adversarial-review fixes in, waiting for the owner's scenario run. Run: `uv run python -m unspootify --mockups`.

## Goal

A desktop app for 4 people (the owner and 3 non-technical friends) that turns a
Spotify playlist into a clean local music library via Soulseek. It must work with
zero terminal use, zero AI help, and no separate installs: download, open, use.

**End state:** one `.dmg` for Apple Silicon Macs (and an AppImage for Linux) that
opens a native app window, bundles everything it needs (`sockseek`, later the tagger),
and walks the user from "export my playlist" to "tagged files in my music folder".

## Decisions (settled; don't re-litigate without the owner)

| Topic | Decision |
|---|---|
| Platforms | Linux first (build and test here), macOS Apple Silicon second. Intel Mac only if cheap (Backlog). No Windows, ever. |
| Stack | Python 3.13 backend, HTML/CSS/JS UI shown in a native window by **pywebview** (no browser, no server, no port). Qt backend on Linux (self-contained in AppImage), native WebKit on macOS. |
| Downloader | **sockseek** (formerly sldl / slsk-batchdl), pinned to v3.0.6, binary bundled per platform, run as a subprocess. Parse `--progress-json` for per-track progress. Soulseek needs no separate client: sockseek connects directly. |
| Input | **Exportify CSV** is the primary path (exportify.net: log in with Spotify, export, done). Direct Spotify links are a Backlog nice-to-have, not relied on. |
| Playlist home | Imported CSVs are copied into an app-managed playlists folder. The app tracks, per playlist and per track, what was tried, downloaded, failed, or skipped. |
| Soulseek login | Username and password fields always visible in the main window. Required on first run, editable any time, remembered between launches. Each friend uses their own account. |
| Folder choice | Native OS folder picker (Finder on Mac, GTK/Qt dialog on Linux). Never make the user type a path. |
| Format | User picks **FLAC or MP3** plus **Automatic** (prefer it, accept what exists: `--pref-format`) or **Force** (only that format: `--format`). In Force mode, report what wasn't found and offer to grab those in the other format. Default: MP3 + Automatic. |
| Naming (pre-tagging) | `Artist/Album [EXT]/NN. Title.ext` via sockseek `--name-format`. The `[EXT]` in the folder keeps encodings of the same album apart. |
| Naming (post-tagging, bonus) | Port the owner's Picard script **ULTIMATE-03** (`Artist/[Year] Album (EP) [FLAC]/NN. Title`, standardized album artist). Source: `~/.config/MusicBrainz/Picard.ini`. |
| Tagging | **Last, bonus phase.** beets as a library (MusicBrainz + AcoustID fingerprinting), headless. Picard itself is not automatable enough to embed. |
| UI layout | Per-track progress list is the main view; collapsible/resizable verbose terminal pane shows raw sockseek output. The window never scrolls: sidebar is fixed (login, playlists, options), only the playlist list, song list, and log scroll. Advanced options open in a sheet (dialog). |
| Looks | Two built-in looks, switchable from the gear (Settings) in the top bar: **Phosphor** (green terminal) and **Jukebox** (early-2000s iTunes-style). Layout in `ui/base.css`, each look in `ui/themes/<name>.css` following `ui/themes/THEMING.md`. |
| Repo | Same repo and name (`unSpootify`), history kept, stays **public**. README is for friends, not developers: short and friendly. Legacy web app moves to `legacy/` in Phase 0 and is deleted at v1. Feature branches + PRs into `main`; Claude handles commits, pushes, PRs, merges. |

## Main-screen sockseek options

Note: in sockseek 3, `-a` applies to string/list inputs; check how CSV rows map to album mode in Phase 2.

- **What to grab:** Just these songs (default) / Full albums (`-a`) / Everything by this artist (`-g`)
- **Format:** FLAC / MP3, Automatic / Force (see Decisions)
- **Try harder** (`-d`)
- **Skip what I already have** (on by default: sockseek index + `--skip-music-dir <library>`)
- **Get album art** (`--album-art`)
- **Advanced (collapsed):** first N tracks (`-n`), skip N (`-o`), fast mode (`--fast-search`), min bitrate, strict title/artist matching, listen port, raw extra flags

## Phases

Each phase ends with a commit/PR. **Checkpoints** mean stop and get the owner's approval before continuing.

### Phase 0: Repo and skeleton
- [x] Move legacy web app (`public/`, `server/`, `runSldl.js`, `package.json`) into `legacy/`; ASCII logo to `assets/logo-ascii.txt`
- [x] Python project: `pyproject.toml`, `src/unspootify/`, managed with `uv`
- [x] `scripts/fetch_sockseek.sh`: download pinned, checksummed sockseek binaries into `vendor/sockseek/<platform>/` (gitignored)
- [x] pywebview window opens on Linux with a placeholder page; JS-to-Python bridge proven (`--smoke-test`)
- [x] `.gitignore`, friend-facing README with roadmap

### Phase 1: v0 UI directions (CHECKPOINT)
- [x] 3 visual directions (A Phosphor, B Jukebox 2003, C Midnight) in the real window with fake data and simulated downloads (`--mockups`)
- [x] Each shows: login fields, folder picker (real native dialog), playlist list, options, per-track progress, resizable verbose pane
- [x] Owner picked: keep Phosphor + Jukebox, drop Midnight (recorded under Decisions)
- [x] Round 2: fixed sidebar, Advanced as a sheet, gear + Settings look picker, Phosphor titles inside boxes, tighter Jukebox styling, theme contract (`THEMING.md`)
- [x] Owner signed off on round 2; Settings became a labeled toolbar button (Ctrl/Cmd+,)
- [x] Adversarial review (fresh agent): fixed HTML injection from names, stacked timers, empty-state crashes, hard-coded counts, frozen rows after Stop, splitter overflow, header misalignment, RTL truncation, tooltips, all-fail messaging, focus/keyboard, contrast, Restore Defaults
- [x] Fake-data scenario picker (10 scenarios, `TEST DATA` corner menu) for the final UI test
- [x] Owner's test round 1 fixes: centered gear (SVG), Retry/Test connection sized like Download, playlists list scrolls (not the sidebar), browse other playlists while downloading, built-in port test with suggested new port, Jukebox focus rings on segments, min window 940x760
- [x] Second adversarial review (regressions): fixed empty button area while browsing, sidebar focus/click loss during background updates, port model (blocks every search), stale port-test results, Phosphor sidebar overflow at 761-780px, focus loss in the port test, Stop available from any playlist
- [ ] Owner runs the final verification

### Phase 2: Pipeline core (no UI wiring)
- [ ] Settings store (login, library folder, last options) in the OS app-data dir
- [ ] Playlist home: import Exportify CSV, copy into playlists folder, parse tracks
- [ ] Per-track state store (SQLite): pending / searching / downloading / done / failed / skipped, with format and path
- [ ] sockseek runner: build args from options, stream output, parse per-track progress and results, cancel cleanly
- [ ] Force-format flow: collect not-found tracks, re-run them in the other format on request
- [ ] Skip-existing across runs
- [ ] Small CLI entry point to run the whole pipeline headless for testing
- [ ] Tests for arg building, CSV parsing, output parsing, state transitions

### Phase 3: Wire the UI
- [ ] JS-to-Python bridge (pywebview `js_api`), live progress events to the page
- [ ] Login fields, native folder picker, CSV import (button + drag-and-drop)
- [ ] "Get your playlist" guide: button opens Exportify in the default browser, short illustrated steps
- [ ] Options panel, start/stop, per-track list, resizable verbose pane
- [ ] Force-format follow-up dialog; end-of-run summary
- [ ] Friendly errors for the predictable failures (bad login, port blocked, no results, folder missing)
- [ ] Real port test (mockup simulates it): check the listen port is reachable from outside (e.g. Soulseek's own port checker), suggest and apply a new port if blocked

### Phase 4: Linux AppImage = v1 (CHECKPOINT)
- [ ] PyInstaller build with sockseek bundled; wrap as AppImage
- [ ] Test on a clean machine/VM: download, open, export, import, download
- [ ] Delete `legacy/`, rewrite README for end users, tag `v1.0.0`

### Phase 5: macOS Apple Silicon `.dmg`
- [ ] GitHub Actions `macos-14` runner builds `.app` (PyInstaller) + `.dmg`
- [ ] First-launch instructions for unsigned app (right-click > Open)
- [ ] Friend test on a real Apple Silicon Mac; fix what breaks

### Phase 6 (bonus): Tagging and canonical naming
- [ ] Bundle beets + `fpcalc`; run after each album/track completes (sockseek `--on-complete` or post-run batch)
- [ ] Port ULTIMATE-03 naming, including album-artist standardization (replaces Picard's album-artist-extension and featartist plugins)
- [ ] Unmatched files go to a "Needs review" folder, never get guessed tags
- [ ] Dedup: never two encodings of one album in the same folder

## Backlog (not now)
- Queue: add more playlists while a download runs
- Intel Mac `.dmg` (second Actions runner, `osx-x64` sockseek)
- Paste a direct Spotify/YouTube/Bandcamp/SoundCloud link (sockseek supports these; Spotify is unreliable)
- Upgrade sockseek to 3.1.x (`--desperate` becomes `--fallback-level`; length matching no longer required by default)
- Auto-detect new Exportify CSVs in `~/Downloads`
- Exportify inside the app window instead of the browser
- Auto-update / "new version available" notice
- Make your own look: user drops a CSS file in a Looks folder, Settings lists it; app offers a copy-paste AI prompt (drafted in `ui/themes/THEMING.md`)
- Compact settings panel growing out of the gear sheet (look, defaults, account)
- Other services' CSVs (Bandcamp, Apple Music, via converter sites like TuneMyMusic/Soundiiz): a later version with its own friendly import guide. v1 is Spotify + Exportify only.
- Apple Developer signing + notarization (removes the first-launch warning)

## Risks
- **Spotify:** Exportify depends on Spotify's API staying open to it. If it breaks, fall back to TuneMyMusic/Soundiiz CSV exports (same CSV path).
- **Unsigned macOS app:** Gatekeeper warning on first launch; must be explained in-app/README.
- **Soulseek hit rate:** some tracks won't exist; Force mode and the summary must make that clear, not look like a bug.
- **Linux webview bundling:** Qt WebEngine makes the AppImage ~150 MB but self-contained; acceptable.
- **Untested Mac:** Claude can't run macOS; every Mac build needs a human test.
