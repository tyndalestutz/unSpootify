![unSpootify](assets/images/unSpootify.png)

**Turn your playlists into a music library you actually own.**

Pick a playlist, press Download, and the songs land in your music folder, neatly sorted as
`Artist / Album [MP3] / Song.mp3`. It finds them on Soulseek, a long-running music-sharing network.

> **v1.0.0 for Linux is out.** The Mac version is in beta testing. Tell us what's confusing or broken (see [Feedback](#feedback)).

## Install

Download the newest file from **[Releases](../../releases)** (test builds are marked *Pre-release*).

| Computer | File |
|---|---|
| Linux (64-bit Intel/AMD) | `unSpootify-…-x86_64.AppImage` |
| Mac (Apple Silicon) | coming in the next beta |

### Linux
1. Download `unSpootify-…-x86_64.AppImage` (about 220 MB).
2. Allow it to run: right-click the file → **Properties** → **Permissions** → tick **Allow executing file as program**.
   (Or in a terminal: `chmod +x unSpootify-*.AppImage`.)
3. Double-click it. Nothing else to install. You can move the file anywhere, e.g. into a `~/Applications` folder.
   Don't run it with `sudo`; it runs as you, like any app.

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
- [ ] Mac app (Apple Silicon)
- [ ] Later: download several playlists in a row, automatic tagging and tidy file names

---

<sub>Powered by [sockseek](https://github.com/fiso64/sockseek) and Soulseek. For private use. Not affiliated with Spotify. Developers: see [PLAN.md](PLAN.md).</sub>
