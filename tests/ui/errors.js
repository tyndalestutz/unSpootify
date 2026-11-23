// Not logged in (scenario: loggedOut): Download disabled with a reason until login is typed.
T.run([
  ["needs login", async () => {
    T.check("Download disabled without login", T.$("#goBtn").disabled && T.$("#goBtn").title.includes("username"));
    T.check("top display asks for login", T.text("#lcdTitle").includes("username"), T.text("#lcdTitle"));
    T.type("#user", "me"); T.type("#pass", "pw");
    await T.waitFor(() => !T.$("#goBtn").disabled, 2000, "enabled");
    T.check("typing a login enables Download", true);
  }],
]);
