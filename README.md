![unSpootify](assets/images/unSpootify.png)

**Turn your playlists into a music library you actually own.**

Pick a playlist, press Download, and the songs land in your music folder, neatly sorted as
`Artist / Album [MP3] / Song.mp3`. It finds them on Soulseek, a long-running music-sharing network.

## Get it

Go to **[Releases](../../releases)** and download the file for your computer:

- **Linux:** `unSpootify-…-x86_64.AppImage`
- **Mac (Apple Silicon):** coming soon

### Linux
1. Right-click the downloaded file → **Properties** → **Permissions** → tick **Allow executing file as program**.
2. Double-click it. That's it, nothing else to install.

## First run

1. **Soulseek login:** type any username and password. No account? Just make one up; it's created the first time you connect. Keep the same one from then on.
2. **Save to:** click **Choose…** and pick where your music should go (default: your Music folder).
3. **Get my playlist:** follow the short guide. On Spotify, [Exportify](https://exportify.net/) saves a playlist as a CSV file in two clicks. For other apps (Apple Music, YouTube, Tidal…) use [Soundiiz](https://soundiiz.com/).
4. **Add CSV file…** (or drop the file on the window), then press **Download**.

## Good to know

- **What to grab:** *These songs* (just the playlist), *Full albums*, or *Whole artist*.
- **Format:** MP3 or FLAC. *Automatic* takes the other format when yours isn't available; *Force* only takes yours and then offers the missing ones in the other format.
- **Already have it?** Songs already in your folder are skipped.
- **Something not found?** Press **Retry** (it searches harder). If *nothing* downloads, press **Test connection**: some school, work and public Wi-Fi networks block Soulseek.
- **Two looks:** click **Settings** (top right) to switch between *Phosphor* and *Jukebox*.

## Roadmap

- [x] Plan it out
- [x] App skeleton
- [x] Pick the look
- [x] Downloading works (MP3/FLAC, full albums, whole artist, skip what you have)
- [ ] Linux app (v1.0.0)
- [ ] Mac app (Apple Silicon)
- [ ] Bonus: automatic tagging and tidy file names

---

<sub>Powered by [sockseek](https://github.com/fiso64/sockseek) and Soulseek. For private use. Not affiliated with Spotify. Developers: see [PLAN.md](PLAN.md).</sub>
