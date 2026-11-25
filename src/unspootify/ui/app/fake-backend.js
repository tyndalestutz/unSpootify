// FakeBackend: implements the same contract as the Python backend with fake data and a simulated
// downloader. Used for the look check (`--mockups`), plain-browser previews, and scripted UI tests.
// Pick a scenario from the TEST DATA corner menu (or ?scn=name).

(() => {
  const BASE = [
    ["Mr. Brightside", "The Killers", "Hot Fuss"],
    ["Float On", "Modest Mouse", "Good News for People Who Love Bad News"],
    ["Take Me Out", "Franz Ferdinand", "Franz Ferdinand"],
    ["Maps", "Yeah Yeah Yeahs", "Fever to Tell"],
    ["Seven Nation Army", "The White Stripes", "Elephant"],
    ["Hey Ya!", "OutKast", "Speakerboxxx/The Love Below"],
    ["Such Great Heights", "The Postal Service", "Give Up"],
    ["Last Nite", "The Strokes", "Is This It"],
    ["The Way We Get By", "Spoon", "Kill the Moonlight"],
    ["Rebellion (Lies)", "Arcade Fire", "Funeral"],
    ["Ocean Breathes Salty", "Modest Mouse", "Good News for People Who Love Bad News"],
    ["Time to Pretend", "MGMT", "Oracular Spectacular"],
    ["Young Folks", "Peter Bjorn and John", "Writer's Block"],
    ["New Slang", "The Shins", "Oh, Inverted World"],
    ["Hysteric", "Yeah Yeah Yeahs", "Fever to Tell"],
    ["1901", "Phoenix", "Wolfgang Amadeus Phoenix"],
    ["Daft Punk Is Playing at My House", "LCD Soundsystem", "LCD Soundsystem"],
    ["Little Sister", "Queens of the Stone Age", "Lullabies to Paralyze"],
  ];
  const LONG = [
    ["Symphony No. 9 in D minor, Op. 125 'Choral': IV. Presto – Allegro assai – Andante maestoso – Allegro energico, sempre ben marcato (Live at Royal Albert Hall, 1998 Remaster)", "Berliner Philharmoniker, Herbert von Karajan, Gundula Janowitz, Hilde Rössel-Majdan, Waldemar Kmentt, Walter Berry, Wiener Singverein", "Beethoven: The Complete Symphonies (Deluxe 40th Anniversary Edition) [Disc 5]"],
    ["Λευκός Θόρυβος", "Σωκράτης Μάλαμας", "Ως το τέλος"],
    ["سلام عليكم وأهلاً بكم في عالم الموسيقى", "عمرو دياب", "تملي معاك"],
    ["שיר לשלום", "להקת הנח\"ל", "שירים"],
    ["夜に駆ける", "YOASOBI", "THE BOOK"],
    ["강남스타일 (Gangnam Style)", "싸이 (PSY)", "싸이6甲 Part 1"],
    ["🔥🔥 FIRE 🔥🔥 (feat. 💀)", "Lil 🅱️ruh 👨‍👩‍👧‍👦", "🎶"],
    ["Supercalifragilisticexpialidociousandthensomemorewithoutanyspacesatallwhatsoever", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "Z"],
    ["", "", ""],
    ["Zalgo T̸̢͎̓h̷̰̉ḛ̶̀ ̵̣͝Ẁ̴̺ä̵͇́l̸͚̈́l̵̳̀", "Ṫ̷̨ę̴̇s̸̥̈t̵͉̿", "Ṁ̴̧ö̷̤́"],
    ["Normal Song", "Normal Artist", "Normal Album"],
  ];
  const INJECT = [
    ["<img src=x onerror=\"document.body.style.transform='rotate(3deg)'\">", "Artist & <i>Friends</i>", "<script>alert(1)</script>"],
    ["<b>Bold?</b> & \"quotes\" & 'apostrophes'", "AC/DC", "Back in <Black>"],
    ["Normal Song", "Normal Artist", "Normal Album"],
  ];
  const OTHERS = [
    { name: "liked songs", total: 412, done: 251 },
    { name: "sunday morning", total: 24, done: 24 },
    { name: "gym (don't judge)", total: 37, done: 0 },
  ];
  const USERS = ["vinylghost", "flac_attack", "mp3dad99", "lowendtheory", "sk8_or_die", "crate_digger"];
  const BLOCKED_PORT = 49998;

  const SCENARIOS = {
    normal: { label: "1 · Normal run", main: ["road trip '03", BASE], others: OTHERS,
      fail: (i) => i === 7 || i === 13, have: (i) => i === 2, flacOnly: (i) => i === 5, warm: 4 },
    longnames: { label: "2 · Long names, unicode, emoji",
      main: ["my absolutely enormous summer 2024 road trip playlist for the drive from Vancouver to Tijuana 🚗🌴", LONG],
      others: [{ name: "مختارات عربية", total: 3, done: 1 }, { name: "שירים טובים", total: 5, done: 0 }, { name: "a", total: 0, done: 0 }],
      fail: (i) => i === 1 || i === 6, have: (i) => i === 3,
      path: "/media/me/My Passport Ultra 2TB/Backups/Music Library (do not delete)/unSpootify downloads" },
    injection: { label: "3 · Weird characters (& < > quotes)", main: ["<b>bold?</b> & <i>friends</i>", INJECT], others: OTHERS },
    huge: { label: "4 · Huge (2,400 songs, 60 playlists)",
      main: ["everything", Array.from({ length: 2400 }, (_, i) => [`Track number ${i + 1}`, `Artist ${i % 97}`, `Album ${i % 31}`])],
      others: Array.from({ length: 60 }, (_, i) => ({ name: `playlist ${i + 1}`, total: 10000 + i, done: 9999 })),
      fail: () => Math.random() < 0.05, have: () => Math.random() < 0.1, speed: 6 },
    allfail: { label: "5 · Everything fails (blocked port)", main: ["obscure b-sides", BASE], others: OTHERS,
      fail: () => Math.random() < 0.1, portBlocked: true },
    allhave: { label: "6 · Already have everything", main: ["sunday morning", BASE], others: OTHERS, have: () => true },
    emptyPlaylist: { label: "7 · Empty playlist", main: ["new playlist", []], others: OTHERS },
    noPlaylists: { label: "8 · First launch (no playlists)", main: null, others: [] },
    loggedOut: { label: "9 · Not logged in", main: ["road trip '03", BASE], others: OTHERS, loggedOut: true },
    tiny: { label: "10 · Two songs", main: ["tiny", [["A", "B", "C"], ["D", "E", "F"]]], others: [], fail: (i) => i === 1 },
    network: { label: "11 · Network blocks Soulseek", main: ["road trip '03", BASE], others: OTHERS, noServer: true },
  };

  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const clone = (x) => JSON.parse(JSON.stringify(x));

  class FakeBackend {
    constructor(api) {
      this.api = api; // pywebview api when running in the app window (native folder picker)
      this.listener = () => {};
      const params = new URLSearchParams(location.search);
      let saved = null;
      try { saved = localStorage.getItem("unspootify.scenario"); } catch {}
      this.scnName = SCENARIOS[params.get("scn")] ? params.get("scn") : SCENARIOS[saved] ? saved : "normal";
      this.scn = SCENARIOS[this.scnName];
      this.settings = {
        username: this.scn.loggedOut ? "" : "ipod_dreamer", password: this.scn.loggedOut ? "" : "hunter22",
        library_path: this.scn.path || "~/Music/unSpootify", look: "phosphor",
        options: { grab: "songs", format: "mp3", mode: "auto", skip_existing: true, album_art: true, try_harder: false },
        advanced: { first_n: null, skip_n: null, fast: false, strict_title: false, min_bitrate: null, listen_port: null, convert_mp3: false },
      };
      try { this.settings.look = localStorage.getItem("unspootify.look") || "phosphor"; } catch {}
      if (params.get("theme")) this.settings.look = params.get("theme");
      this.playlists = [];
      this.data = {}; // id -> tracks (with hidden fail/have flags)
      if (this.scn.main) this.addPlaylist(this.scn.main[0], this.scn.main[1], this.scn);
      for (const o of this.scn.others) this.addSummary(o);
      if (this.scn.warm && this.playlists[0]) {
        for (const t of this.tracks(this.playlists[0].id).slice(0, this.scn.warm)) this.finish(t, true);
        this.summarize(this.playlists[0].id);
      }
      this.timer = null; this.active = null; this.followup = false;
      this.ready = true;
      this.mountPicker();
    }

    on(fn) { this.listener = fn; }
    emit(ev) { setTimeout(() => this.listener(ev), 0); }
    log(bold, text = "") { this.emit({ type: "log", bold, text }); }
    error(code, message, action) { return { error: { code, message, action } }; }

    // ---- data ----
    addPlaylist(name, rows, rules = {}) {
      const id = `pl-${this.playlists.length + 1}`;
      this.data[id] = rows.map(([title, artist, album], i) => ({
        index: i, title, artist, album, length_ms: 200000, state: "queued", pct: 0, format: null, user: null, path: null, reason: null,
        _fail: !!(rules.fail && rules.fail(i)), _have: !!(rules.have && rules.have(i)), _flacOnly: !!(rules.flacOnly && rules.flacOnly(i)),
      }));
      this.playlists.push({ id, name, total: rows.length, done: 0, downloaded: 0, skipped: 0, failed: 0, finished: false,
        archived: false, added_at: this.clock() });
      if (this.listener) this.log("Added playlist ", `"${name}" (${rows.length} songs)`);
      return this.playlists[this.playlists.length - 1];
    }
    addSummary(o) {
      const id = `pl-${this.playlists.length + 1}`;
      this.playlists.push({ id, name: o.name, total: o.total, done: o.done, downloaded: o.done, skipped: 0, failed: 0, finished: false,
        archived: false, added_at: this.clock(), _lazy: true });
    }
    // scenario playlists sort newest-first in the order listed; later imports are newer still
    clock() { this._t = this._t === undefined ? 1000 : this._t - 1; return this.ready ? 2000 + this.playlists.length : this._t; }
    tracks(id) {
      const p = this.playlists.find((x) => x.id === id);
      if (p && p._lazy && !this.data[id]) {
        const n = Math.min(p.total, 3000);
        this.data[id] = Array.from({ length: n }, (_, i) => {
          const [title, artist, album] = BASE[i % BASE.length];
          const t = { index: i, title, artist, album, length_ms: 200000, state: "queued", pct: 0, format: null, user: null, path: null, reason: null,
            _fail: Math.random() < 0.08, _have: false, _flacOnly: false };
          if (i < p.done) { t._fail = false; this.finish(t, true); }
          return t;
        });
      }
      return this.data[id] || [];
    }
    summarize(id) {
      const p = this.playlists.find((x) => x.id === id), t = this.tracks(id);
      const c = (s) => t.filter((x) => x.state === s).length;
      Object.assign(p, { total: t.length, downloaded: c("done"), skipped: c("skipped"), failed: c("failed") });
      p.done = p.downloaded + p.skipped;
      return p;
    }
    public(p) { const { _lazy, ...rest } = p; return clone(rest); }
    publicTrack(t) { const { _el, _key, _fail, _have, _flacOnly, ...rest } = t; return clone(rest); }

    // ---- contract commands ----
    async getState() {
      return { settings: clone(this.settings), playlists: this.playlists.map((p) => this.public(p)),
               run: this.active ? { playlist_id: this.active, running: true } : null, app_version: "fake", offline_test: false };
    }
    async saveSettings(partial) {
      for (const [k, v] of Object.entries(partial)) {
        if (v && typeof v === "object") Object.assign(this.settings[k], v); else this.settings[k] = v;
      }
      try { localStorage.setItem("unspootify.look", this.settings.look); } catch {}
      return clone(this.settings);
    }
    async chooseFolder() {
      if (this.api?.choose_folder) return this.api.choose_folder();
      return "/home/you/Music/Picked Folder";
    }
    async importCsv() {
      const p = this.addPlaylist(`imported playlist ${this.playlists.length + 1}`, BASE.slice(0, 6));
      return this.public(p);
    }
    async importCsvData(name, base64) {
      const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
      const text = new TextDecoder("utf-8").decode(bytes);
      const lines = text.split(/\r?\n/).filter((l) => l.trim());
      if (lines.length < 2) return this.error("CSV_NO_TRACKS", "That CSV has no songs in it.", null);
      const rows = lines.slice(1).map((l) => { const c = l.split(","); return [c[0] || "", c[1] || "", c[2] || ""]; });
      return this.public(this.addPlaylist(name.replace(/\.(csv|txt)$/i, ""), rows));
    }
    async openUrl(which) { this.log("Opened ", which === "soundiiz" ? "soundiiz.com in your browser" : "exportify.net in your browser"); }
    async getTracks(id) { return this.tracks(id).map((t) => this.publicTrack(t)); }

    async start(id, opts = {}) {
      if (this.active) return this.error("ALREADY_RUNNING", "A download is already running.", null);
      if (!this.settings.username || !this.settings.password) return this.error("NO_LOGIN", "Enter a Soulseek username and password first.", "focus_login");
      const p = this.playlists.find((x) => x.id === id);
      const t = this.tracks(id);
      const a = this.settings.advanced;
      let rows = t.slice(a.skip_n || 0);
      if (a.first_n) rows = rows.slice(0, a.first_n);
      rows = opts.only ? rows.filter((x) => opts.only.includes(x.index)) : rows.filter((x) => x.state === "queued");
      if (!rows.length) {
        p.finished = !t.some((x) => x.state === "queued");
        this.emit({ type: "run_finished", playlist_id: id, stopped: false, counts: this.public(this.summarize(id)), missing_format: null, force_format: null, nothing_to_do: true });
        return { ok: true, nothing_to_do: true };
      }
      this.active = id; this.queue = rows; this.stopped = false;
      this.format = opts.format || this.settings.options.format;
      this.force = opts.force ?? this.settings.options.mode === "force";
      this.followup = !!opts.followup;
      p.finished = false;
      this.emit({ type: "run_started", playlist_id: id, total: rows.length });
      this.log("Starting ", `"${p.name}" · ${rows.length} songs to try`);
      if (this.scn.noServer) {
        await wait(1500);
        this.active = null;
        this.emit({ type: "error", code: "NO_NETWORK", message: "Can't reach Soulseek. Check your internet connection.", action: "test_connection", detail: "connection refused" });
        this.emit({ type: "run_finished", playlist_id: id, stopped: false, counts: this.public(this.summarize(id)), missing_format: null, force_format: null });
        return { ok: true };
      }
      this.timer = setInterval(() => this.tick(), 220);
      return { ok: true };
    }

    portOk() { return !this.scn.portBlocked || (this.settings.advanced.listen_port || BLOCKED_PORT) !== BLOCKED_PORT; }

    update(t, fields) {
      Object.assign(t, fields);
      this.emit({ type: "track", playlist_id: this.active, ...this.publicTrack(t) });
    }
    finish(t, quiet) {
      if (t._have && this.settings.options.skip_existing !== false) { Object.assign(t, { state: "skipped", pct: 100, format: null }); if (!quiet) this.log("Already have: ", `${t.artist} - ${t.title}`); return; }
      const wrongFormat = this.force && this.format === "mp3" && t._flacOnly;
      if (t._fail || wrongFormat || (!quiet && !this.portOk())) { Object.assign(t, { state: "failed", pct: 0, format: null, reason: "not_found" }); if (!quiet) this.log("Not found: ", `${t.artist} - ${t.title}`); return; }
      const fmt = t.format || (t._flacOnly ? "FLAC" : this.force ? this.format.toUpperCase() : Math.random() < 0.8 ? "MP3" : "FLAC");
      Object.assign(t, { state: "done", pct: 100, format: fmt, reason: null, path: `${this.settings.library_path}/${t.artist}/${t.album} [${fmt}]/${String(t.index + 1).padStart(2, "0")}. ${t.title}.${fmt.toLowerCase()}` });
      if (!quiet) this.log("Saved: ", t.path);
    }

    tick() {
      const speed = this.scn.speed || 1;
      const active = this.queue.filter((t) => ["searching", "downloading"].includes(t.state));
      for (let guard = 0; active.length < 2 && guard < 500; guard++) {
        const next = this.queue.find((t) => t.state === "queued");
        if (!next) break;
        if (next._have && this.settings.options.skip_existing !== false) { this.finish(next); this.update(next, {}); continue; }
        next._wait = Math.max(1, Math.round((4 + Math.random() * 6) / speed));
        this.update(next, { state: "searching" });
        this.log("Searching: ", `${next.artist} - ${next.title}`);
        active.push(next);
      }
      for (const t of active) {
        if (t.state === "searching" && --t._wait <= 0) {
          const willFail = t._fail || !this.portOk() || (this.force && this.format === "mp3" && t._flacOnly);
          if (willFail) { this.finish(t); this.update(t, {}); continue; }
          const fmt = t._flacOnly ? "FLAC" : this.force ? this.format.toUpperCase() : Math.random() < 0.8 ? "MP3" : "FLAC";
          this.update(t, { state: "downloading", user: USERS[Math.floor(Math.random() * USERS.length)], format: fmt, pct: 0 });
        } else if (t.state === "downloading") {
          const pct = Math.min(100, t.pct + (3 + Math.random() * 8) * speed);
          if (pct >= 100) { this.finish(t); this.update(t, {}); } else this.update(t, { pct: Math.floor(pct) });
        }
      }
      if (!this.queue.some((t) => ["queued", "searching", "downloading"].includes(t.state))) this.end(false);
    }

    end(stopped) {
      clearInterval(this.timer);
      this.timer = null;
      const id = this.active;
      if (stopped) for (const t of this.queue) if (["searching", "downloading"].includes(t.state)) this.update(t, { state: "queued", pct: 0, user: null, format: null });
      const p = this.summarize(id);
      p.finished = !stopped;
      const missing = !stopped && this.force && !this.followup ? p.failed : 0;
      this.active = null;
      this.log(stopped ? "Stopped" : "Finished ", stopped ? " by you. Press Download to continue." : `"${p.name}"`);
      this.emit({ type: "run_finished", playlist_id: id, stopped, counts: this.public(p), missing_format: missing || null, force_format: missing ? this.format : null });
    }

    async stop() { if (this.active) this.end(true); return { ok: true }; }
    async retry(id) {
      const failed = this.tracks(id).filter((t) => t.state === "failed");
      for (const t of failed) { t.state = "queued"; t.reason = null; t._fail = Math.random() < (this.scn.portBlocked ? 0.15 : 0.5); }
      this.log("Retrying ", `${failed.length} songs with Try harder`);
      return this.start(id, { only: failed.map((t) => t.index) });
    }
    async archivePlaylist(id, archived) {
      const p = this.playlists.find((x) => x.id === id);
      p.archived = !!archived;
      return this.public(p);
    }
    async removePlaylist(id) {
      if (this.active === id) return this.error("ALREADY_RUNNING", "A download is already running.", null);
      this.playlists = this.playlists.filter((x) => x.id !== id);
      delete this.data[id];
      return { ok: true };
    }
    async resetPlaylist(id) {
      if (this.active === id) return this.error("ALREADY_RUNNING", "A download is already running.", null);
      for (const t of this.tracks(id)) Object.assign(t, { state: "queued", pct: 0, format: null, user: null, path: null, reason: null });
      const p = this.summarize(id);
      p.finished = false;
      return this.public(p);
    }
    async forceFollowup(id, accept, forcedFormat) {
      if (!accept) return { ok: true };
      const failed = this.tracks(id).filter((t) => t.state === "failed");
      for (const t of failed) { t.state = "queued"; t.reason = null; }
      const other = (forcedFormat || this.settings.options.format) === "mp3" ? "flac" : "mp3";
      return this.start(id, { only: failed.map((t) => t.index), format: other, force: true, followup: true });
    }
    async checkUpdate() { await wait(600); return { available: false, current: "fake", latest: "fake" }; }
    async installUpdate() { return { ok: true }; }
    async testPort(port) {
      this.log("Connection test", ` · checking Soulseek and port ${port}`);
      await wait(1400);
      if (this.scn.noServer) return { open: null, port, server: false };
      const open = this.portOk() && !(this.scn.portBlocked && port === BLOCKED_PORT);
      return open ? { open: true, port, server: true } : { open: false, port, server: true, suggested_port: 50000 + Math.floor(Math.random() * 9000) };
    }

    // ---- TEST DATA corner menu ----
    mountPicker() {
      const label = document.createElement("label");
      label.className = "test-data";
      label.textContent = "TEST DATA ";
      const sel = document.createElement("select");
      sel.id = "scenarioPick";
      for (const [k, s] of Object.entries(SCENARIOS)) {
        const o = document.createElement("option");
        o.value = k; o.textContent = s.label; o.selected = k === this.scnName;
        sel.append(o);
      }
      sel.addEventListener("change", () => {
        try { localStorage.setItem("unspootify.scenario", sel.value); } catch {}
        const url = new URL(location.href);
        url.searchParams.set("scn", sel.value);
        location.href = url.toString();
      });
      label.append(sel);
      document.body.append(label);
    }
  }

  window.FakeBackend = FakeBackend;
  window.FAKE_SCENARIOS = SCENARIOS;
})();
