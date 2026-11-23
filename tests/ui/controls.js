// Every control in the contract's "UI element -> contract map", against the FakeBackend (scenario: normal).
const B = () => window.UI.backend;
T.run([
  ["login fields show and save settings", async () => {
    T.check("login shows saved username", T.$("#user").value === "ipod_dreamer", T.$("#user").value);
    T.type("#user", "new_name");
    await T.waitFor(() => B().settings.username === "new_name", 3000, "username saved");
    T.check("typing username saves it", true);
  }],
  ["playlist click loads it", async () => {
    T.click("#playlistList li[data-idx='2']");
    await T.waitFor(() => T.text("#playlistTitle") === "sunday morning", 3000, "title");
    await T.waitFor(() => document.querySelectorAll("#trackRows .track-row").length === 24, 3000, "24 rows");
    T.check("clicking a playlist shows its songs", true);
    T.click("#playlistList li[data-idx='0']");
    await T.waitFor(() => document.querySelectorAll("#trackRows .track-row").length === 18, 3000, "back to 18");
  }],
  ["guide sheet", async () => {
    T.click("#getPlaylist");
    T.check("Get my playlist opens the guide", T.visible("#guideSheet .sheet"));
    T.click("#openSoundiiz");
    await T.waitFor(() => T.text("#log").includes("soundiiz"), 2000, "log");
    T.check("Open Soundiiz asks the backend to open the site", true);
    T.click("#guideSheet [data-close]");
    T.check("Close closes the guide", T.$("#guideSheet").hidden);
  }],
  ["add csv", async () => {
    const before = window.UI.playlists.length;
    T.click("#addCsv");
    await T.waitFor(() => window.UI.playlists.length === before + 1, 3000, "new playlist");
    T.check("Add CSV adds and selects the playlist", window.UI.current === window.UI.playlists[before].id);
  }],
  ["drop csv", async () => {
    const before = window.UI.playlists.length;
    const dt = new DataTransfer();
    dt.items.add(new File(["Title,Artist,Album\nSong A,Band,LP\nSong B,Band,LP\n"], "dropped mix.csv", { type: "text/csv" }));
    window.dispatchEvent(new DragEvent("drop", { dataTransfer: dt, bubbles: true }));
    await T.waitFor(() => window.UI.playlists.length === before + 1, 3000, "dropped playlist");
    T.check("dropping a CSV adds it", T.text("#playlistTitle") === "dropped mix", T.text("#playlistTitle"));
    const dt2 = new DataTransfer();
    dt2.items.add(new File(["x"], "photo.jpg"));
    window.dispatchEvent(new DragEvent("drop", { dataTransfer: dt2, bubbles: true }));
    await T.waitFor(() => T.$(".lcd").classList.contains("lcd-bad"), 2000, "error shown");
    T.check("dropping a non-CSV shows an error", true);
    T.click("#playlistList li[data-idx='0']");
  }],
  ["choose folder", async () => {
    T.click("#chooseFolder");
    await T.waitFor(() => B().settings.library_path === "/home/you/Music/Picked Folder", 3000, "saved path");
    T.check("Choose… saves the folder and shows it", T.$("#folderPath").title === "/home/you/Music/Picked Folder");
  }],
  ["options save", async () => {
    T.click("#grabSeg [data-value='albums']");
    T.click("#fmtSeg [data-value='flac']");
    T.click("#modeSeg [data-value='force']");
    T.$("#optHarder").click();
    T.$("#optSkip").click();
    await T.waitFor(() => B().settings.options.grab === "albums" && B().settings.options.try_harder === true, 3000, "options");
    const o = B().settings.options;
    T.check("What to grab / Format / Force / toggles save", o.format === "flac" && o.mode === "force" && o.skip_existing === false, JSON.stringify(o));
    T.check("format hint follows choices", T.text("#fmtHint").startsWith("Only FLAC"), T.text("#fmtHint"));
    T.click("#grabSeg [data-value='songs']"); T.click("#fmtSeg [data-value='mp3']"); T.click("#modeSeg [data-value='auto']");
    T.$("#optHarder").click(); T.$("#optSkip").click();
    await T.waitFor(() => B().settings.options.mode === "auto" && B().settings.options.skip_existing, 3000, "options back");
  }],
  ["advanced sheet", async () => {
    T.click("#openAdvanced");
    T.type("#advFirst", "5"); T.type("#advBitrate", "256"); T.$("#advFast").click(); T.type("#listenPort", "51000");
    T.click("#advancedSheet .btn.default");
    await T.waitFor(() => B().settings.advanced.first_n === 5 && B().settings.advanced.listen_port === 51000, 3000, "advanced saved");
    T.check("Advanced fields save on OK", B().settings.advanced.fast === true && B().settings.advanced.min_bitrate === 256);
    T.click("#openAdvanced");
    T.click("#restoreDefaults");
    await T.waitFor(() => B().settings.advanced.first_n === null && B().settings.advanced.listen_port === null, 3000, "defaults");
    T.check("Restore Defaults resets advanced", T.$("#advFirst").value === "" && !T.$("#advFast").checked);
  }],
  ["port test", async () => {
    T.click("#portTestBtn");
    T.check("port test shows progress", T.text("#portResult").startsWith("Testing"), T.text("#portResult"));
    await T.waitFor(() => !T.text("#portResult").startsWith("Testing"), 4000, "result");
    T.check("port test shows the result", T.text("#portResult").includes("is open"), T.text("#portResult"));
    T.click("#advancedSheet .btn.default");
  }],
  ["look picker", async () => {
    T.click("#openSettings");
    T.click(".look-card[data-look='jukebox']");
    await T.waitFor(() => B().settings.look === "jukebox", 3000, "look saved");
    T.check("Look picker switches and saves", document.body.dataset.theme === "jukebox");
    T.click(".look-card[data-look='phosphor']");
    T.click("#settingsSheet [data-close]");
  }],
  ["download, stop, resume", async () => {
    T.click("#goBtn");
    await T.waitFor(() => T.text("#goBtn") === "Stop", 3000, "Stop button");
    await T.waitFor(() => window.UI.tracks[window.UI.current].some((t) => t.state === "downloading"), 8000, "a download");
    T.check("Download starts a run (button turns to Stop, sidebar marker)", T.$("#playlistList li.busy") !== null);
    T.click("#playlistList li[data-idx='1']");
    await T.waitFor(() => T.text("#playlistTitle") === "liked songs", 3000, "browse");
    T.check("browsing during a run keeps Stop available", T.text("#goBtn") === "Stop" && !T.$("#goBtn").disabled);
    T.check("top display names the downloading playlist", T.text("#lcdSub").includes("road trip"), T.text("#lcdSub"));
    T.click("#goBtn");
    await T.waitFor(() => T.text("#goBtn") === "Download" && !window.UI.run, 3000, "stopped");
    T.click("#playlistList li[data-idx='0']");
    await T.waitFor(() => T.text("#lcdTitle").startsWith("Stopped"), 3000, "Stopped message");
    T.check("Stop returns in-flight songs to Waiting", !window.UI.tracks[window.UI.current].some((t) => ["searching", "downloading"].includes(t.state)));
  }],
  ["finish and retry", async () => {
    T.click("#goBtn");
    await T.waitFor(() => !window.UI.run && window.UI.playlists[0].finished && T.visible("#retryBtn"), 60000, "run finished");
    T.check("finished run shows a summary", T.text("#lcdTitle").startsWith("Finished"), T.text("#lcdTitle"));
    T.check("Retry appears for missing songs", T.visible("#retryBtn") && T.text("#retryBtn").startsWith("Retry 2"), T.text("#retryBtn"));
    T.click("#retryBtn");
    await T.waitFor(() => window.UI.run, 3000, "retry started");
    await T.waitFor(() => !window.UI.run, 30000, "retry finished");
    T.check("Retry runs only the missing songs", true);
  }],
  ["details pane", async () => {
    T.check("Details shows the downloader log", T.text("#log").includes("Searching"));
    T.click("#toggleTerm");
    T.check("Hide collapses Details", T.$(".app").classList.contains("term-hidden"));
    T.click("#toggleTerm");
  }],
]);
