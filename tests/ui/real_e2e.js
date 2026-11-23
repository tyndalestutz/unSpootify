// Real window + real Python backend + real sockseek (offline mock share). Placeholders filled by the test.
const CSV_TEXT = __CSV__;
const LIB = __LIB__;
const rows = () => window.UI.tracks[window.UI.current] || [];
T.run([
  ["backend is real", async () => {
    T.check("page talks to the Python backend", window.UI.backend.constructor.name === "RealBackend");
    T.check("offline test mode is announced", T.text("#log").includes("Offline test mode"));
  }],
  ["settings round trip", async () => {
    await window.UI.backend.saveSettings({ library_path: LIB });
    T.type("#user", "e2e_user"); T.type("#pass", "secret");
    await T.sleep(600);
    const s = (await window.UI.backend.getState()).settings;
    T.check("login typed in the window reaches the backend", s.username === "e2e_user" && s.password === "secret");
    window.UI.settings = s;
  }],
  ["import by drop", async () => {
    const dt = new DataTransfer();
    dt.items.add(new File([CSV_TEXT], "road trip.csv", { type: "text/csv" }));
    window.dispatchEvent(new DragEvent("drop", { dataTransfer: dt, bubbles: true }));
    await T.waitFor(() => T.text("#playlistTitle") === "road trip" && document.querySelectorAll("#trackRows .track-row").length === 8, 10000, "imported");
    T.check("dropped CSV becomes a playlist with 8 songs", true);
  }],
  ["download", async () => {
    T.click("#goBtn");
    await T.waitFor(() => T.text("#goBtn") === "Stop", 5000, "Stop");
    await T.waitFor(() => !window.UI.run && T.visible("#retryBtn"), 90000, "finished");
    const st = rows().map((t) => t.state);
    T.check("7 downloaded, 1 not found", st.filter((s) => s === "done").length === 7 && st[7] === "failed", st.join(","));
    T.check("song rows say Done / Not found", T.text("#trackRows .track-row:nth-child(1) .c-status") === "Done" && T.text("#trackRows .track-row:nth-child(8) .c-status") === "Not found");
    T.check("row tooltip shows where it was saved", T.$("#trackRows .track-row").title.includes("/The Killers/Hot Fuss [MP3]/Mr. Brightside.mp3"), T.$("#trackRows .track-row").title);
    T.check("top display summarises", T.text("#lcdTitle") === "Finished: 7 of 8 in your library", T.text("#lcdTitle"));
    T.check("sidebar count updated", T.text("#playlistList li.sel .pl-count") === "7/8", T.text("#playlistList li.sel .pl-count"));
  }],
  ["retry", async () => {
    T.click("#retryBtn");
    await T.waitFor(() => window.UI.run, 5000, "retry started");
    await T.waitFor(() => !window.UI.run, 60000, "retry done");
    T.check("Retry searched again and still can't find the missing song", rows()[7].state === "failed");
  }],
  ["nothing left", async () => {
    T.check("after a finished run, Download says Download again and Retry is offered", T.text("#goBtn") === "Download again" && T.visible("#retryBtn"), T.text("#goBtn"));
  }],
  ["port field saves", async () => {
    T.click("#openAdvanced");
    T.type("#listenPort", "51234");
    T.click("#advancedSheet .btn.default");
    await T.sleep(400);
    const s = (await window.UI.backend.getState()).settings;
    T.check("Advanced listen port reaches the backend", s.advanced.listen_port === 51234, JSON.stringify(s.advanced));
  }],
]);
