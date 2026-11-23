// RealBackend: the Python backend via pywebview. Commands -> window.pywebview.api.*,
// events arrive as window CustomEvent("unspootify", {detail}). A failed call never rejects:
// it resolves to {error: {code, message, action}} like the backend's own errors.
class RealBackend {
  constructor(api) {
    this.api = api;
    this.listener = () => {};
    window.addEventListener("unspootify", (e) => this.listener(e.detail));
  }
  on(fn) { this.listener = fn; }
  async call(name, ...args) {
    try {
      return await this.api[name](...args);
    } catch (e) {
      return { error: { code: "UNEXPECTED", message: "Something went wrong. Details has more.", action: null, detail: String(e) } };
    }
  }
  getState() { return this.call("get_state"); }
  saveSettings(partial) { return this.call("save_settings", partial); }
  chooseFolder() { return this.call("choose_folder"); }
  importCsv() { return this.call("import_csv"); }
  importCsvData(name, base64) { return this.call("import_csv_data", name, base64); }
  openUrl(which) { return this.call("open_url", which); }
  getTracks(id) { return this.call("get_tracks", id); }
  start(id) { return this.call("start", id); }
  stop() { return this.call("stop"); }
  retry(id) { return this.call("retry", id); }
  forceFollowup(id, accept, forcedFormat) { return this.call("force_followup", id, accept, forcedFormat || null); }
  resetPlaylist(id) { return this.call("reset_playlist", id); }
  testPort(port) { return this.call("test_port", port); }
}
window.RealBackend = RealBackend;
