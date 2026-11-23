![unSpootify](assets/images/unSpootify.png)

**Turn your playlists into a music library you actually own.**

Pick a playlist, press Download, and the songs land in your music folder, neatly sorted as
`Artist / Album [MP3] / Song.mp3`. It finds them on Soulseek, a long-running music-sharing network.

> **Linux: v1.0.0. Mac (Apple chip and Intel): in testing (v1.0.1 release candidates).** Tell us what's confusing or broken (see [Feedback](#feedback)).

## Install

Download the newest file from **[Releases](../../releases)** (test builds are marked *Pre-release*).

| Computer | File |
|---|---|
| Linux (64-bit Intel/AMD) | `unSpootify-…-x86_64.AppImage` |
| Mac with Apple chip (M1, M2, M3…) | `unSpootify-…-arm64.dmg` |
| Mac with Intel chip | `unSpootify-…-x86_64.dmg` |

Not sure which Mac you have? Apple menu → **About This Mac**: "Chip: Apple M…" means Apple chip, "Processor: Intel" means Intel.

### Linux
1. Download `unSpootify-…-x86_64.AppImage` (about 220 MB).
2. Allow it to run: right-click the file → **Properties** → **Permissions** → tick **Allow executing file as program**.
   (Or in a terminal: `chmod +x unSpootify-*.AppImage`.)
3. Double-click it. Nothing else to install. You can move the file anywhere, e.g. into a `~/Applications` folder.
   Don't run it with `sudo`; it runs as you, like any app.

### Mac
1. Open the downloaded `.dmg` and **drag unSpootify onto the Applications folder** (don't open it from the dmg window).
2. Open **Applications** and double-click unSpootify. macOS says it can't check the app: click **Done**.
3. Open **System Settings → Privacy & Security**, scroll down, click **Open Anyway** next to "unSpootify was blocked",
   enter your Mac password, then **Open Anyway** again. Only needed once.
4. If macOS asks whether **sockseek** may accept incoming connections, click **Allow** (it's the part that talks to Soulseek).

No "Open Anyway" button? Open **Terminal** and paste `xattr -dr com.apple.quarantine /Applications/unSpootify.app`, then open the app again.

### Linux troubleshooting
If double-clicking does nothing, run it from a terminal (`./unSpootify-*.AppImage`) to see why. On some
minimal systems it needs FUSE (`sudo apt install fuse3`), or you can run it with
`./unSpootify-*.AppImage --appimage-extract-and-run`.

## First run

1. **Soulseek login:** type a username and password. No account? Make one up; it's created the first
   time you connect. Keep using the same one.
2. **Save to:** click **Choose…** and pick where your music goes (default: `Music/unSpootify`).
3. **Get my playlist:** the guide walks you through it.
   - **Spotify:** [Exportify](https://exportify.net/): log in, click **Export** next to a playlist, a CSV downloads.
   - **Apple Music, YouTube, Tidal…:** [Soundiiz](https://soundiiz.com/): export the playlist as **CSV**.
4. **Add CSV file…** (or drag the file onto the window), then press **Download**.

## Tips

- **What to grab:** *These songs* (just the playlist), *Full albums*, or *Whole artist*.
- **Format:** MP3 or FLAC. *Automatic* takes the other format when yours isn't shared; *Force* only takes
  yours, then offers the missing ones in the other format.
- **Already have it?** Songs already in your folder show *Already have* and aren't downloaded again.
- **Not found / Couldn't download:** press **Retry** (it searches harder). If *nothing* downloads,
  press **Test connection**: school, work and some public Wi-Fi block Soulseek.
- **Playlists:** right-click one (or click **⋯**) to download, archive or remove it. Removing never deletes your music.
- **Looks:** **Settings** (top right) switches between *Phosphor* and *Jukebox*.

## Feedback

Open an issue on GitHub (**Issues → New issue**) or just message the person who sent you the app. Most useful:
what you clicked, what you expected, what happened, and a screenshot. If a download misbehaved, copy the last
few lines from the **Details** pane.

## Start fresh (testers)

unSpootify keeps its settings and playlists here (your music folder is separate and never touched):

- Linux: `~/.local/share/unSpootify`
- Mac: `~/Library/Application Support/unSpootify`

Quit the app and delete that folder to start as a brand-new user.

## Roadmap

- [x] Downloading works (MP3/FLAC, full albums, whole artist, skip what you have)
- [x] Linux app (v1.0.0)
- [ ] Mac app (Apple chip + Intel): in testing
- [ ] Later: download several playlists in a row, automatic tagging and tidy file names

---

<sub>Powered by [sockseek](https://github.com/fiso64/sockseek) and Soulseek. For private use. Not affiliated with Spotify. Developers: see [PLAN.md](PLAN.md).</sub>
