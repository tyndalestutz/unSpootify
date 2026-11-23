// unSpootify UI. Talks to a backend that implements docs/ui-contract.md:
//   commands: async methods (getState, saveSettings, chooseFolder, importCsv, importCsvText, openUrl,
//             getTracks, start, stop, retry, forceFollowup, testPort)
//   events:   backend.on(fn) delivers {type: run_started|track|run_finished|log|error|port_result, ...}
// The same code runs against FakeBackend (look check, UI tests) and RealBackend (pywebview + Python).
// Every user-supplied string goes through esc() or textContent.

const $ = (s) => document.querySelector(s);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const LABEL = { queued: "Waiting", searching: "Searching…", waiting: "Waiting (Soulseek limit)", done: "Done", skipped: "Already have", failed: "Not found" };
const BUSY = ["searching", "waiting", "downloading"];
const DEFAULT_PORT = 49998;

const UI = {
  backend: null, settings: null, offline: false,
  playlists: [], current: null, tracks: {}, run: null, // run = {playlist_id}
  flash: null, notice: null, lastUserScroll: 0, renderedFor: undefined, renderedLen: -1,
};

/* ================= helpers ================= */

const byId = (id) => UI.playlists.find((p) => p.id === id) || null;
const currentPl = () => byId(UI.current);
const activePl = () => (UI.run ? byId(UI.run.playlist_id) : null);
const tracksOf = (id) => UI.tracks[id] || null;
const isError = (r) => r && typeof r === "object" && r.error;

function counts(id) {
  const t = tracksOf(id);
  const p = byId(id);
  if (!t) return p ? { n: p.total, done: p.downloaded, skipped: p.skipped, failed: p.failed, queued: p.total - p.done - p.failed } : { n: 0, done: 0, skipped: 0, failed: 0, queued: 0 };
  const c = { n: t.length, done: 0, skipped: 0, failed: 0, queued: 0 };
  for (const x of t) {
    if (x.state === "done") c.done++;
    else if (x.state === "skipped") c.skipped++;
    else if (x.state === "failed") c.failed++;
    else if (x.state === "queued") c.queued++;
  }
  return c;
}

function syncPlaylistCounts(id) {
  const p = byId(id), t = tracksOf(id);
  if (!p || !t) return;
  const c = counts(id);
  Object.assign(p, { total: c.n, downloaded: c.done, skipped: c.skipped, failed: c.failed, done: c.done + c.skipped });
}

function log(bold, rest = "") {
  const logEl = $("#log");
  const atBottom = logEl.scrollHeight - logEl.scrollTop - logEl.clientHeight < 30;
  const line = document.createElement("span");
  const b = document.createElement("b");
  b.textContent = bold;
  line.append(`${new Date().toTimeString().slice(0, 8)}  `, b, `${rest}\n`);
  logEl.append(line);
  while (logEl.childNodes.length > 3000) logEl.firstChild.remove();
  if (atBottom) logEl.scrollTop = logEl.scrollHeight;
}

function setPath(full) {
  const el = $("#folderPath");
  el.title = full || "";
  const parts = (full || "").split("/");
  el.textContent = full && full.length > 32 && parts.length > 3 ? `…/${parts.slice(-2).join("/")}` : full || "";
}

function flashLcd(a, b, ms = 3000, kind = "") {
  UI.flash = { a, b, kind, until: Date.now() + ms };
  render();
  setTimeout(render, ms + 50);
}

function showError(err) {
  // err = {code, message, action}
  UI.notice = { message: err.message, action: err.action, until: Date.now() + 12000 };
  log("Problem: ", err.message + (err.detail ? ` (${err.detail.split("\n").pop()})` : ""));
  if (err.action === "focus_login") (UI.settings && !UI.settings.username ? $("#user") : $("#pass")).focus();
  if (err.action === "choose_folder") $("#chooseFolder").focus();
  if (err.action === "playlist_guide") openSheet("#guideSheet");
  if (err.action === "test_connection") $("#testBtn").hidden = false;
  render();
  setTimeout(render, 12050);
}

/* ================= settings <-> controls ================= */

let saveTimer = null, pendingSave = {};
function saveSettings(partial, immediate = false) {
  for (const [k, v] of Object.entries(partial)) {
    pendingSave[k] = typeof v === "object" && v && !Array.isArray(v) ? { ...(pendingSave[k] || {}), ...v } : v;
  }
  clearTimeout(saveTimer);
  const flush = async () => {
    const body = pendingSave;
    pendingSave = {};
    const r = await UI.backend.saveSettings(body);
    if (r && !isError(r)) UI.settings = r;
  };
  if (immediate) return flush();
  saveTimer = setTimeout(flush, 350);
}

function applySettings(s) {
  UI.settings = s;
  $("#user").value = s.username || "";
  $("#pass").value = s.password || "";
  setPath(s.library_path);
  chooseSeg("#grabSeg", s.options.grab);
  chooseSeg("#fmtSeg", s.options.format);
  chooseSeg("#modeSeg", s.options.mode);
  $("#optSkip").checked = !!s.options.skip_existing;
  $("#optArt").checked = !!s.options.album_art;
  $("#optHarder").checked = !!s.options.try_harder;
  fillAdvanced(s.advanced);
  setLook(s.look, false);
  updateFmtHint();
}

function fillAdvanced(a) {
  $("#advFirst").value = a.first_n ?? "";
  $("#advSkip").value = a.skip_n ?? "";
  $("#advFast").checked = !!a.fast;
  $("#advStrict").checked = !!a.strict_title;
  $("#advBitrate").value = a.min_bitrate ?? "";
  $("#listenPort").value = a.listen_port ?? "";
}

function readAdvanced() {
  const num = (id) => { const v = $(id).value.trim(); return v === "" ? null : Number.parseInt(v, 10); };
  return {
    first_n: num("#advFirst"), skip_n: num("#advSkip"), fast: $("#advFast").checked,
    strict_title: $("#advStrict").checked, min_bitrate: num("#advBitrate"), listen_port: num("#listenPort"),
  };
}

const currentPort = () => { const v = $("#listenPort").value.trim(); return v === "" ? DEFAULT_PORT : Number(v); };

/* ================= playlists & tracks ================= */

async function loadTracks(id) {
  const r = await UI.backend.getTracks(id);
  if (isError(r)) { showError(r.error); return; }
  UI.tracks[id] = r;
  syncPlaylistCounts(id);
}

async function selectPlaylist(id) {
  UI.current = id;
  render();
  if (id && !tracksOf(id)) {
    await loadTracks(id);
    render();
  }
}

function addPlaylist(p) {
  const existing = byId(p.id);
  if (existing) Object.assign(existing, p);
  else UI.playlists.push(p);
  delete UI.tracks[p.id];
  log("Added playlist ", `"${p.name}" (${p.total} songs)`);
  selectPlaylist(p.id);
}

async function importCsv() {
  const r = await UI.backend.importCsv();
  if (!r) return;
  if (isError(r)) return showError(r.error);
  addPlaylist(r);
}

/* ================= events from the backend ================= */

let rafPending = false;
function scheduleRender() {
  if (rafPending) return;
  rafPending = true;
  requestAnimationFrame(() => { rafPending = false; render(); });
}

function onEvent(ev) {
  switch (ev.type) {
    case "run_started": {
      UI.run = { playlist_id: ev.playlist_id };
      const p = byId(ev.playlist_id);
      if (p) p.finished = false;
      UI.notice = null;
      break;
    }
    case "track": {
      const list = tracksOf(ev.playlist_id);
      if (list && list[ev.index]) {
        Object.assign(list[ev.index], {
          state: ev.state, pct: ev.pct, format: ev.format, user: ev.user, path: ev.path, reason: ev.reason,
        });
        syncPlaylistCounts(ev.playlist_id);
      }
      break;
    }
    case "run_finished": {
      UI.run = null;
      const p = byId(ev.playlist_id);
      if (p && ev.counts) Object.assign(p, ev.counts);
      if (ev.nothing_to_do) flashLcd("Nothing left to download", "Everything in this playlist has been tried.");
      if (ev.missing_format && ev.force_format) {
        const other = ev.force_format === "mp3" ? "FLAC" : "MP3";
        $("#followText").textContent =
          `${ev.missing_format} song${ev.missing_format === 1 ? "" : "s"} couldn't be found as ${ev.force_format.toUpperCase()}. ` +
          `Try to get ${ev.missing_format === 1 ? "it" : "them"} as ${other} instead?`;
        $("#followYes").textContent = `Get as ${other}`;
        $("#followupSheet").dataset.playlist = ev.playlist_id;
        openSheet("#followupSheet");
      }
      if (!ev.stopped && UI.current !== ev.playlist_id && p) {
        flashLcd(`Finished “${p.name}”`, `${p.done.toLocaleString()} of ${p.total.toLocaleString()} in your library`, 6000);
      }
      break;
    }
    case "log":
      log(ev.bold || "", ev.text || "");
      return;
    case "error":
      showError(ev);
      return;
    case "port_result":
      showPortResult(ev);
      return;
    case "playlist_added":
      addPlaylist(ev.playlist);
      return;
  }
  // per-song updates are batched to one paint per frame; run start/finish render right away
  if (ev.type === "track") scheduleRender(); else render();
}

/* ================= actions ================= */

function canDownload() {
  const p = currentPl();
  if (!UI.offline && (!$("#user").value.trim() || !$("#pass").value)) return { ok: false, why: "Enter a Soulseek username and password first." };
  if (!p) return { ok: false, why: "Add a playlist first." };
  if (!p.total) return { ok: false, why: "This playlist has no songs." };
  return { ok: true, why: "" };
}

async function call(promise) {
  const r = await promise;
  if (isError(r)) showError(r.error);
  return r;
}

async function onGo() {
  if (UI.run) { await call(UI.backend.stop()); return; }
  if (!canDownload().ok) return;
  await saveSettings({}, true); // make sure the backend has the latest options
  await call(UI.backend.start(UI.current));
}

/* ================= rendering ================= */

function cell(cls, value, placeholder) {
  return value
    ? `<span class="${cls}" dir="auto" title="${esc(value)}">${esc(value)}</span>`
    : `<span class="${cls} missing">${placeholder}</span>`;
}

function renderTable() {
  const rows = $("#trackRows");
  const list = tracksOf(UI.current);
  UI.renderedFor = UI.current;
  UI.renderedLen = list ? list.length : -1;
  if (!list || !list.length) { rows.innerHTML = ""; return; }
  rows.innerHTML = list.map((t) => `<div class="track-row">
      <span class="c-num">${t.index + 1}</span>
      ${cell("c-title", t.title, "(no title)")}
      ${cell("c-artist", t.artist, "(unknown artist)")}
      ${cell("c-album", t.album, "")}
      <span class="c-fmt"></span>
      <span class="c-status"></span>
    </div>`).join("");
  [...rows.children].forEach((el, k) => { list[k]._el = el; list[k]._key = ""; });
}

function asciiBar(p) { const n = Math.round((p / 100) * 12); return "[" + "#".repeat(n) + ".".repeat(12 - n) + "]"; }

function updateRow(t) {
  const pct = Math.floor(t.pct || 0);
  const key = `${t.state}|${pct}|${t.format}|${t.path}`;
  if (key === t._key || !t._el) return;
  t._key = key;
  t._el.classList.toggle("active", BUSY.includes(t.state));
  t._el.title = t.path ? `Saved to ${t.path}` : t.state === "failed" && t.reason === "wrong_format" ? "Not found in that format" : "";
  t._el.querySelector(".c-fmt").innerHTML = t.format && t.state !== "skipped" && t.state !== "failed" ? `<span>${esc(t.format)}</span>` : "";
  const st = t._el.querySelector(".c-status");
  st.className = `c-status st-${t.state}`;
  st.innerHTML = t.state === "downloading"
    ? `<span class="st-text">${pct}%</span><span class="bar"><i style="width:${pct}%"></i></span><span class="asciibar">${asciiBar(pct)}</span>`
    : `<span class="st-text">${LABEL[t.state] || esc(t.state)}</span>`;
}

function render() {
  const p = currentPl();
  const list = tracksOf(UI.current);
  if (UI.renderedFor !== UI.current || UI.renderedLen !== (list ? list.length : -1)) renderTable();
  if (list) list.forEach(updateRow);
  const c = counts(UI.current);

  const title = $("#playlistTitle");
  title.textContent = p ? p.name : "No playlist yet";
  title.title = p ? p.name : "";
  const countsEl = $("#counts");
  countsEl.textContent = p
    ? `${c.n.toLocaleString()} songs · ${c.done.toLocaleString()} downloaded · ${c.skipped.toLocaleString()} already had · ${c.failed.toLocaleString()} not found`
    : "";
  countsEl.title = countsEl.textContent;
  const empty = $("#emptyState");
  empty.hidden = !!(p && c.n) || (p && !list);
  empty.innerHTML = !p
    ? `<strong>No playlists yet.</strong><br>Click <em>Get my playlist</em> on the left to start.`
    : `<strong>This playlist has no songs.</strong><br>Pick another one, or export it again.`;

  const running = !!UI.run, act = activePl(), can = canDownload();
  const go = $("#goBtn");
  go.textContent = running ? "Stop" : "Download";
  go.classList.toggle("running", running);
  go.disabled = !running && !can.ok;
  go.title = running ? (UI.current === UI.run.playlist_id ? "" : `Stops downloading “${act ? act.name : ""}”`) : go.disabled ? can.why : "";
  go.hidden = !running && !!p && !!p.finished && c.queued === 0 && c.failed > 0;
  const retryBtn = $("#retryBtn");
  retryBtn.hidden = running || !p || !c.failed || !p.finished;
  retryBtn.textContent = `Retry ${c.failed.toLocaleString()} missing`;
  const showTest = !running && ((p && p.finished && c.failed && !c.done) || (UI.notice && ["test_connection"].includes(UI.notice.action)));
  $("#testBtn").hidden = !showTest;

  renderLcd(c, can);
  renderPlaylists();
  followCurrent();
}

function renderLcd(c, can) {
  const t1 = $("#lcdTitle"), t2 = $("#lcdSub"), lcd = $(".lcd");
  const act = activePl();
  const shown = UI.run ? counts(UI.run.playlist_id) : c;
  const shownLib = shown.done + shown.skipped, lib = c.done + c.skipped;
  $("#lcdFill").style.width = shown.n ? `${(shownLib / shown.n) * 100}%` : "0%";
  let a, b, kind = "";
  const actTracks = UI.run ? tracksOf(UI.run.playlist_id) : null;
  const cur = actTracks && (actTracks.find((t) => t.state === "downloading") || actTracks.find((t) => t.state === "searching") || actTracks.find((t) => t.state === "waiting"));
  const p = currentPl();
  if (UI.flash && Date.now() < UI.flash.until) { a = UI.flash.a; b = UI.flash.b; kind = UI.flash.kind; }
  else if (UI.notice && Date.now() < UI.notice.until && !UI.run) { a = UI.notice.message; b = noticeHint(UI.notice.action); kind = "bad"; }
  else if (UI.run && cur) {
    a = `${cur.title || "(no title)"} — ${cur.artist || "(unknown artist)"}`;
    const where = UI.current === UI.run.playlist_id ? "" : `“${act ? act.name : ""}” · `;
    const what = cur.state === "searching" ? "Searching Soulseek…" : cur.state === "waiting" ? "Waiting for Soulseek's search limit…" : `From ${cur.user || "someone"} · ${(shownLib + shown.failed + 1).toLocaleString()} of ${shown.n.toLocaleString()}`;
    b = where + what;
  } else if (UI.run) { a = `Starting “${act ? act.name : ""}”…`; b = "Logging in to Soulseek"; }
  else if (!can.ok) { a = can.why; b = !p ? "Your playlists will show up on the left." : $("#user").value.trim() ? "" : "No account? Just make one up."; }
  else if (p.finished) {
    if (c.failed === c.n) { a = "Nothing was found"; b = "Try Test connection."; }
    else if (c.done === 0 && c.failed === 0) { a = "Nothing new to download"; b = `All ${c.n.toLocaleString()} songs are already in your library.`; }
    else if (c.failed) { a = `Finished: ${lib.toLocaleString()} of ${c.n.toLocaleString()} in your library`; b = `${c.failed.toLocaleString()} couldn't be found. Press Retry to search harder.`; }
    else { a = `Finished: all ${c.n.toLocaleString()} in your library`; b = "Everything was found."; }
  } else if (lib + c.failed > 0 && c.queued) { a = `Stopped: ${lib.toLocaleString()} of ${c.n.toLocaleString()} done`; b = "Press Download to continue."; }
  else { a = "Ready"; b = "Press Download to start."; }
  t1.textContent = a; t1.title = a;
  t2.textContent = b || " ";
  lcd.classList.toggle("lcd-bad", kind === "bad");
}

function noticeHint(action) {
  return { focus_login: "Check your username and password.", choose_folder: "Click Choose… to pick another folder.",
           test_connection: "Press Test connection.", retry: "Press Download to try again.",
           playlist_guide: "Click Get my playlist for help." }[action] || "";
}

function renderPlaylists() {
  const list = $("#playlistList");
  const structure = UI.playlists.map((p) => `${p.id}|${p.name}`).join("\n");
  const meter = (p) => `${p.total ? (Math.min(p.done, p.total) / p.total) * 100 : 0}%`;
  if (list.dataset.structure === structure && UI.playlists.length) {
    [...list.children].forEach((li, i) => {
      const p = UI.playlists[i];
      li.classList.toggle("sel", p.id === UI.current);
      li.classList.toggle("busy", !!UI.run && p.id === UI.run.playlist_id);
      li.setAttribute("aria-selected", p.id === UI.current);
      const count = `${p.done.toLocaleString()}/${p.total.toLocaleString()}`;
      const cEl = li.querySelector(".pl-count");
      if (cEl.textContent !== count) cEl.textContent = count;
      li.querySelector(".pl-meter span").style.width = meter(p);
    });
    return;
  }
  const focusedIdx = document.activeElement?.closest?.("#playlistList li")?.dataset.idx;
  list.dataset.structure = structure;
  list.innerHTML = UI.playlists.map((p, i) => {
    const cls = [p.id === UI.current ? "sel" : "", UI.run && p.id === UI.run.playlist_id ? "busy" : ""].join(" ").trim();
    return `<li class="${cls}" role="option" tabindex="0" aria-selected="${p.id === UI.current}" data-idx="${i}" title="${esc(p.name)}">
      <span class="pl-name" dir="auto">${esc(p.name)}</span>
      <span class="pl-count">${p.done.toLocaleString()}/${p.total.toLocaleString()}</span>
      <span class="pl-meter"><span style="width:${meter(p)}"></span></span>
    </li>`;
  }).join("") || `<li class="pl-empty">Nothing here yet</li>`;
  if (focusedIdx !== undefined) list.querySelector(`li[data-idx="${focusedIdx}"]`)?.focus();
}

function followCurrent() {
  if (!UI.run || UI.current !== UI.run.playlist_id || Date.now() - UI.lastUserScroll < 3000) return;
  const cur = (tracksOf(UI.current) || []).find((t) => BUSY.includes(t.state));
  if (cur && cur._el) cur._el.scrollIntoView({ block: "nearest" });
}

/* ================= port test ================= */

let portTesting = false, portTestId = 0;
function cancelPortTest() { portTestId++; portTesting = false; $("#portTestBtn").removeAttribute("aria-disabled"); }
function setPortResult(text, kind = "", action = null) {
  const el = $("#portResult");
  el.className = `hint port-result ${kind}`;
  el.textContent = text;
  if (action) {
    const b = document.createElement("button");
    b.className = "btn small";
    b.textContent = action.label;
    b.addEventListener("click", action.run);
    el.append(" ", b);
  }
}
const PORT_IDLE = "If nothing downloads, test your connection. Some networks block Soulseek.";

async function testPort() {
  if (portTesting) return;
  const port = currentPort();
  if (!Number.isInteger(port) || port < 1024 || port > 65535) { setPortResult("Port must be a number between 1024 and 65535.", "bad"); return; }
  const id = ++portTestId;
  portTesting = true;
  $("#portTestBtn").setAttribute("aria-disabled", "true");
  setPortResult(`Testing the connection and port ${port}…`, "testing");
  const r = await UI.backend.testPort(port);
  if (id !== portTestId) return; // defaults restored meanwhile
  portTesting = false;
  $("#portTestBtn").removeAttribute("aria-disabled");
  if (isError(r)) return setPortResult(r.error.message, "bad");
  showPortResult(r);
}

function showPortResult(r) {
  if (!r || r.port === undefined) return;
  if (r.error === "BAD_PORT") return setPortResult("Port must be a number between 1024 and 65535.", "bad");
  if (r.server === false) return setPortResult("This network can't reach Soulseek at all (school, work and some public Wi-Fi block it). Try another network.", "bad");
  if (r.error === "NO_NETWORK") return setPortResult("Couldn't run the test. Check your internet connection.", "bad");
  if (r.open === true) return setPortResult(`Soulseek is reachable and port ${r.port} is open. The connection isn't the problem.`, "good");
  if (r.open === null) return setPortResult("Soulseek is reachable, but the port checker didn't answer clearly. Try again later.", "");
  const suggest = r.suggested_port;
  setPortResult(`Soulseek is reachable, but port ${r.port} is closed. Downloads still work, just slower; another port can help.`, "bad",
    suggest ? {
      label: `Use port ${suggest}`,
      run: () => {
        $("#listenPort").value = suggest;
        saveSettings({ advanced: { listen_port: suggest } }, true);
        setPortResult(`Now using port ${suggest}. Press OK, then Retry.`, "good");
        log("Port changed", ` · now listening on ${suggest}`);
        $("#advancedSheet .btn.default").focus();
      },
    } : null);
}

/* ================= controls ================= */

function chooseSeg(id, value) {
  const btns = [...$(id).querySelectorAll("button")];
  const b = btns.find((x) => x.dataset.value === value) || btns[0];
  btns.forEach((x) => { const on = x === b; x.classList.toggle("on", on); x.setAttribute("aria-checked", on); x.tabIndex = on ? 0 : -1; });
}
const segValue = (id) => $(`${id} .on`).dataset.value;

function updateFmtHint() {
  const fmt = $("#fmtSeg .on").textContent, other = fmt === "MP3" ? "FLAC" : "MP3";
  const force = segValue("#modeSeg") === "force";
  $("#fmtHint").textContent = force ? `Only ${fmt}. Missing songs get offered as ${other}.` : `${fmt} if possible, otherwise anything.`;
}

const LOOKS = ["phosphor", "jukebox"];
function setLook(look, save = true) {
  if (!LOOKS.includes(look)) look = LOOKS[0];
  document.body.dataset.theme = look;
  document.querySelectorAll(".look-card").forEach((c) => c.classList.toggle("on", c.dataset.look === look));
  if (save) saveSettings({ look });
}

let returnFocus = null;
const focusables = (root) => [...root.querySelectorAll("button, input, select, [tabindex='0']")].filter((el) => !el.disabled && el.offsetParent);
function openSheet(id) {
  const open = document.querySelector(".sheet-backdrop:not([hidden])");
  if (open && `#${open.id}` === id) return;
  if (open) open.hidden = true; else returnFocus = document.activeElement;
  $(id).hidden = false;
  focusables($(id))[0]?.focus();
}
function closeSheets() {
  const open = document.querySelector(".sheet-backdrop:not([hidden])");
  if (!open) return;
  open.hidden = true;
  if (open.id === "advancedSheet") saveSettings({ advanced: readAdvanced() }, true);
  returnFocus?.focus?.();
}

function bindControls() {
  $("#goBtn").addEventListener("click", onGo);
  $("#retryBtn").addEventListener("click", () => call(UI.backend.retry(UI.current)));
  $("#testBtn").addEventListener("click", () => { openSheet("#advancedSheet"); testPort(); });
  $("#portTestBtn").addEventListener("click", testPort);

  ["#user", "#pass"].forEach((id) => $(id).addEventListener("input", () => {
    saveSettings({ username: $("#user").value.trim(), password: $("#pass").value });
    if (UI.notice?.action === "focus_login") UI.notice = null;
    render();
  }));
  $(".track-table").addEventListener("wheel", () => (UI.lastUserScroll = Date.now()), { passive: true });
  $(".track-table").addEventListener("mousedown", () => (UI.lastUserScroll = Date.now()));

  $("#playlistList").addEventListener("click", (e) => {
    const li = e.target.closest("li[data-idx]");
    if (li) selectPlaylist(UI.playlists[+li.dataset.idx].id);
  });
  $("#playlistList").addEventListener("keydown", (e) => {
    const li = e.target.closest("li[data-idx]");
    if (!li) return;
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectPlaylist(UI.playlists[+li.dataset.idx].id); }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); (e.key === "ArrowDown" ? li.nextElementSibling : li.previousElementSibling)?.focus(); }
  });

  document.querySelectorAll(".seg").forEach((seg) => {
    const btns = [...seg.querySelectorAll("button")];
    btns.forEach((b) => b.setAttribute("role", "radio"));
    const changed = () => {
      updateFmtHint();
      saveSettings({ options: { grab: segValue("#grabSeg"), format: segValue("#fmtSeg"), mode: segValue("#modeSeg") } });
    };
    seg.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { chooseSeg(`#${seg.id}`, b.dataset.value); changed(); } });
    seg.addEventListener("keydown", (e) => {
      const i = btns.indexOf(document.activeElement);
      if (i < 0 || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return;
      e.preventDefault();
      const n = btns[(i + (e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : btns.length - 1)) % btns.length];
      chooseSeg(`#${seg.id}`, n.dataset.value); n.focus(); changed();
    });
  });
  [["#optSkip", "skip_existing"], ["#optArt", "album_art"], ["#optHarder", "try_harder"]].forEach(([id, key]) =>
    $(id).addEventListener("change", () => saveSettings({ options: { [key]: $(id).checked } })));
  ["#advFirst", "#advSkip", "#advBitrate", "#listenPort"].forEach((id) =>
    $(id).addEventListener("change", () => saveSettings({ advanced: readAdvanced() })));
  ["#advFast", "#advStrict"].forEach((id) => $(id).addEventListener("change", () => saveSettings({ advanced: readAdvanced() })));

  $("#toggleTerm").addEventListener("click", () => {
    const hidden = $(".app").classList.toggle("term-hidden");
    $("#toggleTerm").textContent = hidden ? "Show" : "Hide";
  });

  (() => {
    const app = $(".app"), split = $("#splitter");
    let dragging = false, wanted = 170;
    const apply = () => {
      const max = Math.max(80, window.innerHeight - 400);
      app.style.setProperty("--term-h", `${Math.max(80, Math.min(max, wanted))}px`);
    };
    split.addEventListener("mousedown", (e) => { dragging = true; e.preventDefault(); });
    window.addEventListener("mouseup", () => (dragging = false));
    window.addEventListener("mousemove", (e) => { if (dragging) { wanted = window.innerHeight - e.clientY - 12; apply(); } });
    window.addEventListener("resize", apply);
  })();

  $("#chooseFolder").addEventListener("click", async () => {
    const path = await UI.backend.chooseFolder();
    if (!path || isError(path)) return;
    setPath(path);
    await saveSettings({ library_path: path }, true);
    if (UI.notice?.action === "choose_folder") UI.notice = null;
    render();
  });
  $("#getPlaylist").addEventListener("click", () => openSheet("#guideSheet"));
  $("#addCsv").addEventListener("click", importCsv);
  $("#guideAddCsv").addEventListener("click", () => { closeSheets(); importCsv(); });
  $("#openSoundiiz").addEventListener("click", () => UI.backend.openUrl("soundiiz"));
  $("#openExportify").addEventListener("click", () => UI.backend.openUrl("exportify"));
  $("#followYes").addEventListener("click", () => { const pid = $("#followupSheet").dataset.playlist; closeSheets(); call(UI.backend.forceFollowup(pid, true)); });
  $("#followNo").addEventListener("click", () => { const pid = $("#followupSheet").dataset.playlist; closeSheets(); UI.backend.forceFollowup(pid, false); });

  $("#openAdvanced").addEventListener("click", () => openSheet("#advancedSheet"));
  $("#openSettings").addEventListener("click", () => openSheet("#settingsSheet"));
  document.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", closeSheets));
  document.querySelectorAll(".sheet-backdrop").forEach((bd) => bd.addEventListener("click", (e) => { if (e.target === bd) closeSheets(); }));
  $("#restoreDefaults").addEventListener("click", () => {
    fillAdvanced({ first_n: null, skip_n: null, fast: false, strict_title: false, min_bitrate: null, listen_port: null });
    saveSettings({ advanced: readAdvanced() });
    cancelPortTest();
    setPortResult(PORT_IDLE);
  });
  document.querySelectorAll(".look-card").forEach((c) => c.addEventListener("click", () => setLook(c.dataset.look)));
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeSheets();
    if (e.key === "," && (e.ctrlKey || e.metaKey)) { e.preventDefault(); openSheet("#settingsSheet"); }
    const open = document.querySelector(".sheet-backdrop:not([hidden])");
    if (open && e.key === "Tab") {
      const f = focusables(open), first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  // drop a CSV anywhere: read it in the page and hand the text to the backend
  let dragDepth = 0;
  const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes("Files");
  window.addEventListener("dragenter", (e) => { if (hasFiles(e)) { dragDepth++; $("#dropHint").hidden = false; } });
  window.addEventListener("dragleave", () => { if (--dragDepth <= 0) { dragDepth = 0; $("#dropHint").hidden = true; } });
  window.addEventListener("dragover", (e) => { if (hasFiles(e)) e.preventDefault(); });
  window.addEventListener("drop", async (e) => {
    e.preventDefault();
    dragDepth = 0;
    $("#dropHint").hidden = true;
    const file = e.dataTransfer?.files?.[0];
    if (!file) return;
    if (!/\.(csv|txt)$/i.test(file.name)) return showError({ code: "CSV_UNREADABLE", message: "That file doesn't look like a playlist CSV.", action: "playlist_guide" });
    if (file.size > 50 * 1024 * 1024) return showError({ code: "CSV_UNREADABLE", message: "That file is too big to be a playlist.", action: null });
    const r = await UI.backend.importCsvText(file.name, await file.text());
    if (isError(r)) return showError(r.error);
    if (r) addPlaylist(r);
  });
}

/* ================= start ================= */

async function startApp(backend) {
  UI.backend = backend;
  backend.on(onEvent);
  bindControls();
  setPortResult(PORT_IDLE);
  const state = await backend.getState();
  UI.offline = !!state.offline_test;
  UI.playlists = state.playlists || [];
  UI.run = state.run ? { playlist_id: state.run.playlist_id } : null;
  applySettings(state.settings);
  log(state.offline_test ? "Offline test mode" : "Ready", state.offline_test ? " · downloads come from a local test folder, not Soulseek" : "");
  await selectPlaylist(UI.playlists[0]?.id || null);
  window.unspootifyReady = true;
}

window.startApp = startApp;
window.UI = UI; // for scripted UI checks
