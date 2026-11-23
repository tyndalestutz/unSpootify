// Force MP3 -> follow-up sheet -> get the missing one as FLAC (scenario: normal, Hey Ya! is FLAC-only).
T.run([
  ["force followup", async () => {
    T.click("#modeSeg [data-value='force']");
    await T.sleep(500);
    T.click("#goBtn");
    await T.waitFor(() => !T.$("#followupSheet").hidden, 60000, "follow-up sheet");
    T.check("Force mode offers the missing songs in the other format", T.text("#followYes") === "Get as FLAC", T.text("#followYes"));
    T.click("#followYes");
    await T.waitFor(() => window.UI.run, 3000, "follow-up run");
    await T.waitFor(() => !window.UI.run, 30000, "follow-up done");
    const heyYa = window.UI.tracks[window.UI.current][5];
    T.check("follow-up gets it as FLAC", heyYa.state === "done" && heyYa.format === "FLAC", JSON.stringify(heyYa));
  }],
]);
