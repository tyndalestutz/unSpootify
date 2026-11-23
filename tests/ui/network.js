// Network blocks Soulseek (scenario: network): error in the top display, Test connection explains.
T.run([
  ["network error", async () => {
    T.click("#goBtn");
    await T.waitFor(() => T.$(".lcd").classList.contains("lcd-bad"), 8000, "error");
    T.check("error shows in the top display", T.text("#lcdTitle").includes("Can't reach Soulseek"), T.text("#lcdTitle"));
    await T.waitFor(() => T.visible("#testBtn"), 2000, "Test connection");
    T.click("#testBtn");
    await T.waitFor(() => !T.text("#portResult").startsWith("Testing"), 5000, "result");
    T.check("Test connection explains the network blocks Soulseek", T.text("#portResult").includes("can't reach Soulseek"), T.text("#portResult"));
  }],
]);
