# UI contract

The single source of truth for how the window and the Python backend talk.
Every visible control and every piece of displayed state maps to an entry here.
If it isn't in this file, the UI must not depend on it. If the UI shows it, it's here.

Two implementations satisfy this contract:

- **FakeBackend** (JS, in the page): the Phase 1 mockup simulation, refactored. Used for UI work and UI tests.
- **Real backend** (Python, via pywebview `js_api` + events): drives sockseek.

The UI code is identical for both. Every control below gets a scripted test against the
FakeBackend, and an end-to-end test against the real backend running sockseek in
`--mock-files-dir` mode (offline, no Soulseek account needed).

## Data shapes

```text
Settings   { username, password, library_path, look,
             options: { grab: "songs"|"albums"|"artist", format: "mp3"|"flac",
                        mode: "auto"|"force", skip_existing: bool, album_art: bool, try_harder: bool },
             advanced: { first_n: int|null, skip_n: int|null, fast: bool, strict_title: bool,
                         min_bitrate: int|null, listen_port: int|null } }

Playlist   { id, name, source_file, total, done, failed, skipped, finished: bool, added_at }

Track      { index, title, artist, album, length_ms,
             state: "queued"|"searching"|"waiting"|"downloading"|"done"|"skipped"|"failed",
             pct: 0-100, format: "MP3"|"FLAC"|...|null, user: str|null, path: str|null,
             reason: null|"not_found"|"wrong_format"|"cancelled"|"error" }

Run        { playlist_id, running: bool, current_track: index|null,
             counts: { total, done, skipped, failed, queued } }
```

`waiting` = Soulseek search rate limit (34 searches per ~220 s); the UI shows it as "Waiting (Soulseek limit)".

## Commands (UI → backend)

| Command | Returns | Used by |
|---|---|---|
| `get_state()` | `{settings, playlists, run, app_version, offline_test}` | page load |
| `save_settings(partial)` | `settings` | login fields, options, Advanced OK, look picker |
| `choose_folder()` | `path \| null` | Save to › Choose… |
| `import_csv()` | `playlist \| error` | Add CSV file… (native file dialog) |
| `import_csv_path(path)` | `playlist \| error` | drag-and-drop a CSV onto the window |
| `open_exportify()` | `null` | Get my playlist from Spotify (opens browser + guide) |
| `get_tracks(playlist_id)` | `Track[]` | clicking a playlist |
| `start(playlist_id)` | `ok \| error` | Download |
| `stop()` | `ok` | Stop (works from any playlist; stops the active run) |
| `retry(playlist_id)` | `ok \| error` | Retry N missing (re-queues failed, with Try harder) |
| `force_followup(playlist_id, accept)` | `ok` | Force mode: "get the missing ones as the other format?" |
| `test_port(port)` | `{open, port, server, suggested_port?, error?}` | Advanced › Test port, Test connection |

## Events (backend → UI)

Delivered as `window.dispatchEvent(new CustomEvent("unspootify", {detail}))`.

| Event | Payload | UI effect |
|---|---|---|
| `run_started` | `{playlist_id, total}` | Download → Stop, sidebar ↓ marker |
| `track` | `{playlist_id, ...Track}` | one song row + counts + sidebar meter |
| `run_finished` | `{playlist_id, stopped, counts: Playlist, missing_format, force_format, nothing_to_do?}` | summary in top display, Retry/Test connection, Force follow-up offer when `missing_format` |
| `log` | `{bold, text}` | Details pane line |
| `status` | `{phase: "connecting"\|"logged_in"\|"login_failed"\|"rate_limited"\|"idle"}` | top display |
| `error` | `{code, message, action?}` | top display message + optional action button |
| `port_result` | `{open: bool\|null, port, server: bool, suggested_port?, error?}` | Advanced port result (`server` false = network blocks Soulseek entirely) |

## Error codes (all user-facing text is plain words + what to do)

| Code | Message shown | Action |
|---|---|---|
| `LOGIN_FAILED` | Soulseek didn't accept that username/password. | focus login fields |
| `PORT_BLOCKED` | This network seems to block Soulseek's port. | Test connection |
| `NO_NETWORK` | Can't reach Soulseek. Check your internet. | Retry |
| `FOLDER_MISSING` | The music folder isn't there anymore (unplugged drive?). | Choose… |
| `FOLDER_NOT_WRITABLE` | Can't save into that folder. | Choose… |
| `CSV_UNREADABLE` | That file isn't a playlist CSV. | Get my playlist guide |
| `CSV_NO_TRACKS` | That CSV has no songs in it. | — |
| `SOCKSEEK_MISSING` | Part of the app is missing. Reinstall unSpootify. | — |
| `SOCKSEEK_CRASHED` | The downloader stopped unexpectedly. Details has more. | Retry |
| `NO_LOGIN` | Enter a Soulseek username and password first. | focus login fields |
| `ALREADY_RUNNING` | A download is already running. | — |

`LOGIN_FAILED`, `PORT_BLOCKED` and `NO_NETWORK` are detected from sockseek's text output and only
when a run dies before its summary line; the exact wording must be confirmed with a real account (Phase 3).

## UI element → contract map

| Element | Reads | Writes / calls |
|---|---|---|
| Username / Password | `settings.username/password` | `save_settings` (on change, debounced) |
| Playlists list (+ ↓ marker, meters) | `playlists`, `run.playlist_id`, `track` events | `get_tracks` |
| Get my playlist from Spotify | — | `open_exportify` |
| Add CSV file… / drop | — | `import_csv` / `import_csv_path` |
| Save to + Choose… | `settings.library_path` | `choose_folder` → `save_settings` |
| What to grab / Format / Automatic-Force / toggles | `settings.options` | `save_settings` |
| Advanced sheet fields, Restore Defaults, OK | `settings.advanced` | `save_settings` |
| Test port / Test connection | `port_result` | `test_port` |
| Settings › Look | `settings.look` | `save_settings` |
| Playlist title + counts | selected playlist + its tracks | — |
| Download / Stop | `run`, validation | `start` / `stop` |
| Retry N missing | finished playlist with failed > 0 | `retry` |
| Song rows | `Track` | — |
| Top display (LCD) | `run`, `status`, `error`, `run_finished` | — |
| Details pane | `log` events | — |

## Option → sockseek mapping (verified offline with sockseek 3.0.6)

The app always writes its own input file (normalized lengths in seconds, only the rows still to do),
so `snum` in sockseek maps back to playlist rows through the run manifest.

| Option | How |
|---|---|
| login | `--user`, `--pass` (password scrubbed from every log line) |
| Save to | files staged by sockseek, then moved by `unspootify finalize` (sockseek `--on-complete ... update-index`) to `Artist/Album [EXT]/NN. Title.ext` |
| Just these songs | CSV `Artist,Title,Album,Length` |
| Full albums | CSV `Artist,Album` (title-less rows are album jobs); every song of that album follows the album's state |
| Whole artist | list file of `"artist=NAME"` lines + `-g`; every song by that artist follows the artist's state |
| MP3/FLAC + Automatic | `--pref-format mp3\|flac` |
| MP3/FLAC + Force | `--format mp3\|flac`; misses offered via `run_finished.missing_format`, `force_followup` reruns them with the other format |
| Skip what I already have | sockseek index (per playlist + mode) + `--skip-music-dir <library>`; off = `--no-skip-existing` |
| Get album art | `--album-art largest` (Full albums / Whole artist only) |
| Try harder | `-d` (Retry always adds it) |
| Only first / Skip first | applied by the app when choosing rows (not sockseek `-n/-o`) |
| Fast mode | `--fast-search` |
| Strict title | `--strict-title` |
| Min bitrate | `--min-bitrate` |
| Listen port | `--listen-port` |
| (always) | `--progress-json`, `--no-progress`, `--index-path` |

## sockseek `--progress-json` → events (observed with 3.0.6)

| sockseek event | → |
|---|---|
| `track_list {total, tracks[index,artist,title,album,length]}` | initial `Track[]` (state queued / skipped) |
| `search_start {artist,title,album}` | `track` searching |
| `download_start {artist,title,username,filename,size,extension}` | `track` downloading, user, format |
| `download_progress {jobId,bytesTransferred,totalBytes,percent}` | `track` pct (jobId matched to the `download_start` with the same size) |
| `track_state {…, terminalOutcome: Succeeded, downloadPath}` | `track` done + path |
| `track_state {…, terminalOutcome: Failed, failureReason}` | `track` failed + reason |
| `track_state {…, skipReason}` | `track` skipped |

Notes: sockseek writes from several threads, so JSON and text can share a line; the parser extracts
every JSON object from anywhere in a line. `track_list` order is not playlist order; songs are
matched by artist + title. Album and artist modes also use text lines (`[NNN] AlbumJob: searching:`,
`Album File: downloading:`, `AlbumJob: succeeded/failed`) because their JSON events are per file.
sockseek exits non-zero when some songs fail; that is a normal finish (it prints `[cli] Completed:`).
