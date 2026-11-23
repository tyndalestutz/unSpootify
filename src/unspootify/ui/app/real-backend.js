// RealBackend: the Python backend via pywebview. Commands -> window.pywebview.api.*,
// events arrive as window CustomEvent("unspootify", {detail}).
class RealBackend {
  constructor(api) {
    this.api = api;
    this.listener = () => {};
    window.addEventListener("unspootify", (e) => this.listener(e.detail));
  }
  on(fn) { this.listener = fn; }
  getState() { return this.api.get_state(); }
  saveSettings(partial) { return this.api.save_settings(partial); }
  chooseFolder() { return this.api.choose_folder(); }
  importCsv() { return this.api.import_csv(); }
  importCsvText(name, text) { return this.api.import_csv_text(name, text); }
  openUrl(which) { return this.api.open_url(which); }
  getTracks(id) { return this.api.get_tracks(id); }
  start(id) { return this.api.start(id); }
  stop() { return this.api.stop(); }
  retry(id) { return this.api.retry(id); }
  forceFollowup(id, accept) { return this.api.force_followup(id, accept); }
  testPort(port) { return this.api.test_port(port); }
}
window.RealBackend = RealBackend;
