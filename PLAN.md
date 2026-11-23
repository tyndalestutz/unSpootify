# unSpootify rework plan

> The plan of record. Work happens one phase at a time, in order. New ideas go to
> **Backlog**, not into the current phase. Tick boxes as items land; update the
> **Status** line at the end of every working session.

**Status:** Phase 4 done (Linux v1.0.0, 2026-11-23). Phase 5 planned and reviewed: Mac Apple Silicon (Intel on request) → v1.0.1.

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
| Platforms | Linux first (build and test here), macOS Apple Silicon second. Intel Mac only on request (one CI matrix line, untestable on real hardware). No Windows, ever. |
| Stack | Python 3.13 backend, HTML/CSS/JS UI shown in a native window by **pywebview** (no browser, no server, no port). Qt backend on Linux (self-contained in AppImage), native WebKit on macOS. |
| Downloader | **sockseek** (formerly sldl / slsk-batchdl), pinned to v3.0.6, binary bundled per platform, run as a subprocess. Parse `--progress-json` for per-track progress. Soulseek needs no separate client: sockseek connects directly. |
| Input | **Exportify CSV** is the recommended path (owner found it easiest); **Soundiiz** stays in the guide for other apps (Apple Music, YouTube, Tidal…). The "Get my playlist" guide covers both. Direct Spotify links are out: sockseek 3 needs your own Spotify developer app *and* Premium. |
| Playlist home | Imported CSVs are copied into an app-managed playlists folder. The app tracks, per playlist and per track, what was tried, downloaded, failed, or skipped. |
| Soulseek login | Username and password fields always visible in the main window. Required on first run, editable any time, remembered between launches. Each friend uses their own account. |
| Folder choice | Native OS folder picker (Finder on Mac, GTK/Qt dialog on Linux). Never make the user type a path. |
| Format | User picks **FLAC or MP3** plus **Automatic** (prefer it, accept what exists: `--pref-format`) or **Force** (only that format: `--format`). In Force mode, report what wasn't found and offer to grab those in the other format. Default: MP3 + Automatic. |
| Naming (pre-tagging) | `Artist/Album [EXT]/Title.ext` (first artist only; no track number in songs mode because a playlist position isn't the album track number; album/artist modes keep the file's number). The `[EXT]` in the folder keeps encodings of the same album apart. |
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
- [x] Owner verified; Phase 1 approved and merged (2026-11-23)

### Phase 2: Pipeline core, built to the UI contract
Everything the backend does is shaped by `docs/ui-contract.md` (commands, events, states, error codes).
The backend never invents state the UI can't show, and the UI never shows state the backend can't produce.
- [x] Draft UI contract (`docs/ui-contract.md`): every control and display mapped to a command/event
- [x] De-risk: sockseek reads Exportify CSV columns automatically; `--progress-json` events observed; offline end-to-end works with `--mock-files-dir`
- [x] Offline test library: `scripts/make_mock_library.py` builds tagged audio files (ffmpeg) for a CSV, with deliberate gaps, MP3/FLAC mixes, and an "already have" set
- [x] Recorded sockseek output fixtures (scrubbed paths) for parser tests
- [x] Settings store (OS app-data dir; password stored locally, never logged)
- [x] Playlist store: import CSV (copy into app playlists folder), validate (`CSV_UNREADABLE`, `CSV_NO_TRACKS`), stable playlist ids
- [x] Track state store (SQLite) using the contract's states and reasons
- [x] Option → sockseek args mapping (table in the contract), unit-tested per option
- [x] Full albums (derived title-less CSV) and Whole artist (`-g`) verified with CSV input
- [x] sockseek runner: spawn, parse `--progress-json` into contract events, correlate `download_progress` (jobId) to tracks, detect rate-limit waiting, cancel cleanly, map failures to error codes (login, port, network, folder, crash)
- [x] Force-format follow-up run; skip-existing across runs (index + `--skip-music-dir`)
- [x] Naming: `Artist/Album [EXT]/NN. Title` from source tags (`{sartist}`, `{salbum}`, `{snum}`) with tag fallback
- [x] Port test: listens on the port and asks Soulseek's checker (tools.slsknet.org/porttest.php), plus a direct reachability check of the Soulseek server; returns `{open, server, suggested_port}`
- [x] Headless CLI that emits contract events as JSON lines (same stream the window will consume)
- [x] Tests: CSV parsing, args, event mapping from fixtures, state transitions, end-to-end with the mock library

- [ ] Unverified until a real account is used (Phase 3): sockseek's wording for login failure / blocked network, and how rate-limit waiting is reported

### Phase 3: Wire the UI (no control left unconnected)
- [x] Refactor `mock.js` into a FakeBackend that implements the contract; UI logic moves to `app.js`, shared by fake and real
- [x] Real backend bridge: pywebview `js_api` commands + `unspootify` CustomEvents
- [x] Production page `index.html` from the approved mockup (both looks); TEST DATA picker only in mockup mode
- [x] Every row of the contract's "UI element → contract map" has a scripted check (screenshot_ui.py CHECK) against the FakeBackend
- [x] End-to-end in the real window against sockseek `--mock-files-dir`: import CSV, choose folder, download, stop, browse during run, retry, force follow-up, skip existing, port test, every error code
- [x] "Get your playlist" guide: opens Exportify in the default browser, short illustrated steps
- [x] Real port test wired to Advanced and Test connection
- [x] Adversarial review of the wired app (fresh agent) and fixes: double-click start/stop, failed Retry stranding rows, Full albums after songs, Download again, unlaunchable sockseek, crash-after-success, Only/Skip-first claiming done, password off the command line (private config), log scrubbing, login timeout + status, encodings, follow-up format
- [x] Owner real-account test round 1 (2026-11-23): downloads work. Fixes from it: search with the first artist and without 'Remastered'/'feat.' (multi-artist songs were missed), fast search on by default + 4 concurrent searches (speed), FLAC prefers CD quality (16-bit/48 kHz max) instead of huge hi-res files, no fake track numbers, Exportify first in the guide
- [x] Playlist management (owner request): sort playlists by Date added / Name / Size, Archive (collapsible Archived group), Remove from unSpootify (confirm; music untouched) via right-click / ⋯ / keyboard; click song column headers to sort
- [x] Owner real-account test round 2 (2026-11-23): playlist sort/archive/remove confirmed; removal verified to delete the app's copy, state and run files
- [x] Album-mates searched together + `--pref-strict-album`; failed songs say "Couldn't download" (found but transfer failed) vs "Not found"

### Phase 4: Linux AppImage = v1.0.0 (CHECKPOINT)
Readiness check (2026-11-23, brief fresh-agent review): ready; the three must-fixes below are built into this phase.
Goal: one downloadable `unSpootify-1.0.0-x86_64.AppImage` that opens the app with nothing else installed.

Build
- [x] PyInstaller spec `packaging/unspootify.spec`, **onedir** (sockseek calls the app once per finished song; onefile would unpack ~150 MB each time)
- [x] Entry script `src/unspootify/__main__.py` so the frozen app answers `finalize` (and other CLI commands) without opening a window
- [x] Bundle `ui/` as data and `vendor/sockseek/<platform>/sockseek` as a binary (keeps its exec bit); trim unused Qt modules
- [x] Start sockseek with a clean environment (restore `LD_LIBRARY_PATH_ORIG`; PyInstaller's library path can break the .NET binary)
- [x] App icon: owner picked A (black tile, Spotify-green eject; `assets/icon/`), glossy-black variant kept in `assets/icon/alt/` for later; `.desktop` entry
- [x] AppDir + pinned `appimagetool` → `unSpootify-<version>-x86_64.AppImage` via `scripts/build_appimage.sh`

Verify
- [x] Built-binary tests: `<exe> finalize …` works headless; `--smoke-test` passes on the built app; offline end-to-end (`--offline-test`) through the built app
- [x] Clean-machine test in a fresh Docker container (`packaging/test/clean_linux.sh`, Ubuntu 24.04 + Xvfb): opens, offline download lands in ~/Music/unSpootify (found + fixed: default music folder wasn't created on a fresh home)
- [x] GitHub Actions: tests + AppImage on every PR, attached to tagged releases; `test` and `appimage` are required checks on `main`

Release
- [x] Delete `legacy/`; README rewritten for friends (download, make executable, open; first-run steps; Exportify guide)
- [x] Version 1.0.0 in `pyproject.toml` / `__init__.py`
- [x] Release candidates rc.1–rc.4 (fixed: bundled system libs broke GLX on real desktops; fast search made most songs fail; settings version crash on 2nd launch; AppImage app-menu entry + icon; look flash on start)
- [x] `v1.0.0` released after the owner's checkpoint
- [x] CHECKPOINT: owner downloaded the release AppImage and did real runs (2026-11-23)

### Phase 5: macOS `.dmg` (Apple Silicon; Intel on request) = v1.0.1 (CHECKPOINT: friend test)
Goal: the friend downloads one `.dmg`, drags the app to Applications, approves it once, and uses it with zero terminal.
Version: Linux shipped as v1.0.0; Mac needs code changes, so the first release with Mac is **v1.0.1** (all builds attached).
Claude can't run macOS locally: every Mac check runs on GitHub's Mac runners or with the owner/friend.
Plan reviewed by a fresh agent (2026-11-23); its fixes are folded in below.

Build (CI)
- [ ] Apple Silicon job on `macos-15` (pinned; `macos-14` was retired 2026-11-02), sockseek `osx-arm64`
- [ ] Intel: one extra matrix line (`macos-15-intel`, sockseek `osx-x64`; Intel runners end Fall 2027), **off unless someone
      in the group has an Intel Mac** (friends are on recent Apple Silicon; an Intel build couldn't be tested on real hardware)
- [ ] Same PyInstaller spec, `BUNDLE` → `unSpootify.app` (Cocoa/WebKit via pyobjc, no Qt); version read from `__version__`;
      generate `assets/icon/unspootify.icns` (`iconutil`)
- [ ] Ad-hoc sign inside out (sockseek, dylibs, app) as the last step; the app never writes inside its own bundle
- [ ] `.dmg` (`hdiutil`): the app, an Applications shortcut, and `Open me first.txt`; `unSpootify-<v>-arm64.dmg`
- [ ] Attach the `.dmg` to tagged releases next to the AppImage; the mac job becomes a required check

Verify on the Mac runner, using the app copied *out of the mounted dmg* with a quarantine flag set (as a download would have)
- [ ] `codesign --verify --deep --strict` passes
- [ ] `finalize` answered headless (no window/Dock icon), timed (expect ~0.5–1.5 s cold start per song)
- [ ] Offline end-to-end run through the built app (sockseek launches despite quarantine)
- [ ] `--smoke-test` opens the real Cocoa window; screenshots of both looks are best-effort (runner screen capture can be blank)
- [ ] Quitting (Cmd+Q, red close button, app quit) stops sockseek on every path; CI asserts the process is gone

App changes for macOS
- [ ] On start, remove the quarantine flag from the app's own bundled sockseek (belt and braces)
- [ ] Kill sockseek from the window-closed / app-quit handlers, not only `atexit` (Cocoa can exit without it)
- [ ] App menu: Settings… (Cmd+,) and standard Edit menu so Cmd+C/V/X/A work in text fields
- [ ] App data in `~/Library/Application Support/unSpootify`, music in `~/Music/unSpootify` (already the defaults; confirm)

First launch (unsigned app)
- [ ] Guide in `Open me first.txt`, README and release notes: **drag to Applications first** (running from the dmg/Downloads
      breaks when the dmg is ejected); double-click → blocked → System Settings › Privacy & Security › **Open Anyway** (asks for
      the Mac password); if that button never appears, a one-line Terminal fallback the owner can read out
      (`xattr -dr com.apple.quarantine /Applications/unSpootify.app`); firewall prompt (only if the firewall is on) names
      "sockseek": click Allow

Friend test (CHECKPOINT)
- [ ] Owner or friend installs from the release on a real Mac and does a real run; feedback as GitHub issues; fixes in v1.0.x
- [ ] Decide on an Apple Developer ID ($99/yr) only if the first-launch steps prove too confusing

### Phase 6 (bonus): Tagging and canonical naming
- [ ] Bundle beets + `fpcalc`; run after each album/track completes (sockseek `--on-complete` or post-run batch)
- [ ] Port ULTIMATE-03 naming, including album-artist standardization (replaces Picard's album-artist-extension and featartist plugins)
- [ ] Unmatched files go to a "Needs review" folder, never get guessed tags
- [ ] Dedup: never two encodings of one album in the same folder

## Backlog (not now)
- Queue: add more playlists while a download runs (owner asked again 2026-11-23; next after v1)
- Intel Mac `.dmg`: switch on the `macos-15-intel` matrix line if anyone needs it (runner available until Fall 2027)
- Paste a direct Spotify/YouTube/Bandcamp/SoundCloud link (sockseek supports these; Spotify is unreliable)
- Upgrade sockseek to 3.1.x (`--desperate` becomes `--fallback-level`; length matching no longer required by default)
- Auto-detect new Exportify CSVs in `~/Downloads`
- Exportify inside the app window instead of the browser
- v1.1: built-in update check + install (owner wants it before tagging ships). Sketch: check GitHub's latest release on start (daily) and in Settings; verify a SHA256SUMS asset; Linux swaps the AppImage file in place and relaunches; Mac downloads the dmg, replaces the app via a small helper after quit (no quarantine flag, so no second Open Anyway)
- Make your own look: user drops a CSS file in a Looks folder, Settings lists it; app offers a copy-paste AI prompt (drafted in `ui/themes/THEMING.md`)
- Compact settings panel growing out of the gear sheet (look, defaults, account)
- (moved into v1) Soundiiz covers other services' playlists. Verify Soundiiz's real CSV columns and whether its file export needs a paid plan.
- Report sockseek 3.0.6 fast-search bug upstream ('Sequence contains no elements' when the first pick fails)
- Kill sockseek if the app is force-quit or crashes (atexit + window close cover normal exits; PDEATHSIG can't be used because pywebview spawns from worker threads)
- Remove playlists from the sidebar; handle re-exported playlists with the same name
- Apple Developer signing + notarization (removes the first-launch warning)

## Risks
- **Spotify:** Exportify depends on Spotify's API staying open to it. If it breaks, fall back to TuneMyMusic/Soundiiz CSV exports (same CSV path).
- **Unsigned macOS app:** Gatekeeper warning on first launch; must be explained in-app/README.
- **Soulseek hit rate:** some tracks won't exist; Force mode and the summary must make that clear, not look like a bug.
- **Linux webview bundling:** Qt WebEngine makes the AppImage ~150 MB but self-contained; acceptable.
- **Untested Mac:** Claude can't run macOS; every Mac build needs a human test.
