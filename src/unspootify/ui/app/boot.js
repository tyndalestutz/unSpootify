// Pick the backend: the app window says "real" or "fake" (look check); a plain browser or the
// screenshot tool gets the FakeBackend.
(async () => {
  const params = new URLSearchParams(location.search);
  const hasApi = await new Promise((resolve) => {
    if (window.pywebview?.api?.get_mode) return resolve(true);
    const timer = setTimeout(() => resolve(false), params.has("fake") ? 0 : 1500);
    window.addEventListener("pywebviewready", () => { clearTimeout(timer); resolve(true); }, { once: true });
  });
  const mode = hasApi ? await window.pywebview.api.get_mode() : "fake";
  const api = hasApi ? window.pywebview.api : null;
  window.startApp(mode === "real" ? new window.RealBackend(api) : new window.FakeBackend(api));
})();
