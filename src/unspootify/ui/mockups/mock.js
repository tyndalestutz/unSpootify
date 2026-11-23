// Look-check mockup: fake data + simulated downloads. Nothing here talks to sockseek.
// Every user-supplied string (track/playlist names, paths) goes through esc() or textContent.

const $ = (s) => document.querySelector(s);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ================= fake data ================= */

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
const OTHER_PLAYLISTS = [
  { name: "liked songs", total: 412, done: 251 },
  { name: "sunday morning", total: 24, done: 24 },
  { name: "gym (don't judge)", total: 37, done: 0 },
];
const DEFAULT_PATH = "~/Music/unSpootify";
const USERS = ["vinylghost", "flac_attack", "mp3dad99", "lowendtheory", "sk8_or_die", "crate_digger"];

const SCENARIOS = {
  normal: {
    label: "1 · Normal run",
    main: { name: "road trip '03", rows: BASE }, others: OTHER_PLAYLISTS,
    fail: (i) => i === 7 || i === 13, have: (i) => i === 2, warm: 4,
  },
  longnames: {
    label: "2 · Long names, unicode, emoji",
    main: { name: "my absolutely enormous summer 2024 road trip playlist for the drive from Vancouver to Tijuana 🚗🌴", rows: LONG },
    others: [{ name: "مختارات عربية", total: 3, done: 1 }, { name: "שירים טובים", total: 5, done: 0 }, { name: "a", total: 0, done: 0 }],
    fail: (i) => i === 1 || i === 6, have: (i) => i === 3,
    path: "/media/me/My Passport Ultra 2TB/Backups/Music Library (do not delete)/unSpootify downloads",
  },
  injection: {
    label: "3 · Weird characters (& < > quotes)",
    main: { name: "<b>bold?</b> & <i>friends</i>", rows: INJECT }, others: OTHER_PLAYLISTS,
  },
  huge: {
    label: "4 · Huge (2,400 songs, 60 playlists)",
    main: { name: "everything", rows: Array.from({ length: 2400 }, (_, i) => [`Track number ${i + 1}`, `Artist ${i % 97}`, `Album ${i % 31}`]) },
    others: Array.from({ length: 60 }, (_, i) => ({ name: `playlist ${i + 1}`, total: 10000 + i, done: 9999 })),
    fail: () => Math.random() < 0.05, have: () => Math.random() < 0.1, speed: 6,
  },
  allfail: { label: "5 · Everything fails", main: { name: "obscure b-sides", rows: BASE }, others: OTHER_PLAYLISTS, fail: () => true, alwaysFail: true },
  allhave: { label: "6 · Already have everything", main: { name: "sunday morning", rows: BASE }, others: OTHER_PLAYLISTS, have: () => true },
  emptyPlaylist: { label: "7 · Empty playlist", main: { name: "new playlist", rows: [] }, others: OTHER_PLAYLISTS },
  noPlaylists: { label: "8 · First launch (no playlists)", main: null, others: [] },
  loggedOut: { label: "9 · Not logged in", main: { name: "road trip '03", rows: BASE }, others: OTHER_PLAYLISTS, loggedOut: true },
  tiny: { label: "10 · Two songs", main: { name: "tiny", rows: [["A", "B", "C"], ["D", "E", "F"]] }, others: [], fail: (i) => i === 1 },
};

/* ================= state ================= */

let scn, playlists, current = null, running = false, timer = null, finished = false, lastUserScroll = 0;
const LABEL = { queued: "Waiting", searching: "Searching…", done: "Done", skipped: "Already have", failed: "Not found" };

function mkTracks(rows, s) {
  return rows.map(([title, artist, album], i) => ({
    i: i + 1, title, artist, album, state: "queued", pct: 0, fmt: "", key: "",
    willFail: !!(s.fail && s.fail(i)), have: !!(s.have && s.have(i)),
  }));
}

function loadScenario(name) {
  stopTimer();
  scn = SCENARIOS[name] || SCENARIOS.normal;
  playlists = [];
  if (scn.main) playlists.push({ name: scn.main.name, rows: scn.main.rows, total: scn.main.rows.length, done: 0, tracks: null });
  for (const o of scn.others) playlists.push({ ...o, rows: null, tracks: null });
  $("#user").value = scn.loggedOut ? "" : "ipod_dreamer";
  $("#pass").value = scn.loggedOut ? "" : "hunter22";
  setPath(scn.path || DEFAULT_PATH);
  logEl.textContent = "";
  log("sockseek 3.0.6", " · ready");
  current = null;
  selectPlaylist(playlists.length ? 0 : -1);
  if (scn.warm && current) { for (let k = 0; k < Math.min(scn.warm, current.tracks.length); k++) finish(current.tracks[k], true); }
  renderAll();
}

function tracksFor(p) {
  if (p.tracks) return p.tracks;
  const rows = p.rows || Array.from({ length: Math.min(p.total, 3000) }, (_, i) => BASE[i % BASE.length]);
  p.tracks = mkTracks(rows, p.rows ? scn : { fail: () => Math.random() < 0.08 });
  if (!p.rows) for (let k = 0; k < Math.min(p.done, p.tracks.length); k++) finish(p.tracks[k], true);
  return p.tracks;
}

function selectPlaylist(idx) {
  if (running) { flashLcd("Stop the current download first", "Then pick another playlist."); return; }
  current = idx >= 0 ? playlists[idx] : null;
  if (current) { tracksFor(current); log(`Loaded playlist "${current.name}"`, ` (${current.tracks.length} songs)`); }
  finished = false;
  renderAll();
}

/* ================= simulation ================= */

function finish(t, quiet) {
  if (t.have) { t.state = "skipped"; t.fmt = ""; t.pct = 100; if (!quiet) log("Skipping (already in library): ", `${t.artist} - ${t.title}`); return; }
  if (t.willFail) { t.state = "failed"; t.pct = 0; t.fmt = ""; if (!quiet) log("Not found: ", `${t.artist} - ${t.title}`); return; }
  t.state = "done"; t.pct = 100; t.fmt = t.fmt || (Math.random() < 0.8 ? "MP3" : "FLAC");
  if (!quiet) log("Succeeded: ", `${t.artist}/${t.album} [${t.fmt}]/${String(t.i).padStart(2, "0")}. ${t.title}.${t.fmt.toLowerCase()}`);
}

function tick() {
  const tracks = current.tracks;
  const active = tracks.filter((t) => t.state === "searching" || t.state === "downloading");
  for (let guard = 0; active.length < 2 && guard < 500; guard++) {
    const next = tracks.find((t) => t.state === "queued");
    if (!next) break;
    if (next.have) { finish(next); continue; }
    next.state = "searching"; next.wait = Math.max(1, Math.round((4 + Math.random() * 6) / (scn.speed || 1)));
    log("Searching: ", `${next.artist} - ${next.title}`);
    active.push(next);
  }
  for (const t of active) {
    if (t.state === "searching" && --t.wait <= 0) {
      if (t.willFail) { finish(t); continue; }
      t.user = USERS[Math.floor(Math.random() * USERS.length)];
      t.fmt = Math.random() < 0.8 ? "MP3" : "FLAC";
      t.state = "downloading";
      log(`Found ${20 + Math.floor(Math.random() * 60)} results`, ` · best: ${t.user}  ${t.fmt === "MP3" ? "320kbps" : "16bit/44.1kHz"}  .${t.fmt.toLowerCase()}`);
    } else if (t.state === "downloading") {
      t.pct = Math.min(100, t.pct + (3 + Math.random() * 8) * (scn.speed || 1));
      if (t.pct >= 100) finish(t);
    }
  }
  if (!tracks.some((t) => ["queued", "searching", "downloading"].includes(t.state))) endRun();
  renderAll();
}

function stopTimer() { if (timer) clearInterval(timer); timer = null; running = false; }

function start() {
  if (!canDownload().ok || running) return;
  if (!current.tracks.some((t) => t.state === "queued")) { flashLcd("Nothing left to download", "Everything in this playlist has been tried."); return; }
  stopTimer();
  running = true; finished = false;
  log("Starting download", ` · ${current.tracks.filter((t) => t.state === "queued").length} songs to try`);
  timer = setInterval(tick, 220);
  renderAll();
}

function stop() {
  stopTimer();
  for (const t of current.tracks) if (t.state === "searching" || t.state === "downloading") { t.state = "queued"; t.pct = 0; t.fmt = ""; }
  log("Stopped", " by you. Press Download to continue where you left off.");
  renderAll();
}

function endRun() {
  stopTimer();
  finished = true;
  log("Finished", "");
}

function retry() {
  const failed = current.tracks.filter((t) => t.state === "failed");
  for (const t of failed) { t.state = "queued"; t.willFail = scn.alwaysFail ? true : Math.random() < 0.5; }
  log(`Retrying ${failed.length} songs`, " with Try harder");
  start();
}

/* ================= rendering ================= */

const rowsEl = $("#trackRows");
const logEl = $("#log");
let renderedFor = undefined;

function counts() {
  const t = current ? current.tracks : [];
  const c = (s) => t.filter((x) => x.state === s).length;
  return { n: t.length, done: c("done"), skipped: c("skipped"), failed: c("failed"), queued: c("queued") };
}

function canDownload() {
  if (!$("#user").value.trim() || !$("#pass").value) return { ok: false, why: "Enter a Soulseek username and password first." };
  if (!current) return { ok: false, why: "Add a playlist first." };
  if (!current.tracks.length) return { ok: false, why: "This playlist has no songs." };
  return { ok: true, why: "" };
}

function renderTable() {
  // Build rows once per playlist; ticks only touch rows that changed.
  renderedFor = current;
  if (!current || !current.tracks.length) { rowsEl.innerHTML = ""; return; }
  rowsEl.innerHTML = current.tracks.map((t) => `<div class="track-row">
      <span class="c-num">${t.i}</span>
      ${cell("c-title", t.title, "(no title)")}
      ${cell("c-artist", t.artist, "(unknown artist)")}
      ${cell("c-album", t.album, "")}
      <span class="c-fmt"></span>
      <span class="c-status"></span>
    </div>`).join("");
  [...rowsEl.children].forEach((el, k) => { current.tracks[k].el = el; current.tracks[k].key = ""; });
}

function cell(cls, value, placeholder) {
  return value
    ? `<span class="${cls}" dir="auto" title="${esc(value)}">${esc(value)}</span>`
    : `<span class="${cls} missing">${placeholder}</span>`;
}

function asciiBar(p) { const n = Math.round((p / 100) * 12); return "[" + "#".repeat(n) + ".".repeat(12 - n) + "]"; }

function updateRow(t) {
  const pct = Math.floor(t.pct);
  const key = `${t.state}|${pct}|${t.fmt}`;
  if (key === t.key) return;
  t.key = key;
  const busy = t.state === "searching" || t.state === "downloading";
  t.el.classList.toggle("active", busy);
  t.el.querySelector(".c-fmt").innerHTML = t.fmt ? `<span>${t.fmt}</span>` : "";
  const st = t.el.querySelector(".c-status");
  st.className = `c-status st-${t.state}`;
  st.innerHTML = t.state === "downloading"
    ? `<span class="st-text">${pct}%</span><span class="bar"><i style="width:${pct}%"></i></span><span class="asciibar">${asciiBar(pct)}</span>`
    : `<span class="st-text">${LABEL[t.state]}</span>`;
}

function renderAll() {
  if (renderedFor !== current) renderTable();
  const c = counts();
  if (current) current.tracks.forEach(updateRow);
  if (current) current.done = c.done + c.skipped;

  // header + empty states
  const title = $("#playlistTitle");
  title.textContent = current ? current.name : "No playlist yet";
  title.title = current ? current.name : "";
  $("#counts").textContent = current
    ? `${c.n.toLocaleString()} songs · ${c.done.toLocaleString()} downloaded · ${c.skipped.toLocaleString()} already had · ${c.failed.toLocaleString()} not found`
    : "";
  const empty = $("#emptyState");
  empty.hidden = !!(current && c.n);
  empty.innerHTML = !current
    ? `<strong>No playlists yet.</strong><br>Click <em>Get my playlist from Spotify</em> on the left to start.`
    : `<strong>This playlist has no songs.</strong><br>Pick another one, or export it again from Spotify.`;

  // buttons
  const go = $("#goBtn"), can = canDownload();
  go.textContent = running ? "Stop" : "Download";
  go.classList.toggle("running", running);
  go.disabled = !running && !can.ok;
  go.title = go.disabled ? can.why : "";
  const retryBtn = $("#retryBtn");
  retryBtn.hidden = running || !c.failed;
  retryBtn.textContent = `Retry ${c.failed.toLocaleString()} missing`;

  renderLcd(c, can);
  renderPlaylists();
  followCurrent();
}

let flash = null;
function flashLcd(a, b) { flash = { a, b, until: Date.now() + 2500 }; renderAll(); setTimeout(renderAll, 2600); }

function renderLcd(c, can) {
  const t1 = $("#lcdTitle"), t2 = $("#lcdSub");
  const lib = c.done + c.skipped;
  $("#lcdFill").style.width = c.n ? `${(lib / c.n) * 100}%` : "0%";
  let a, b;
  const cur = current && (current.tracks.find((t) => t.state === "downloading") || current.tracks.find((t) => t.state === "searching"));
  if (flash && Date.now() < flash.until) { a = flash.a; b = flash.b; }
  else if (running && cur) {
    a = `${cur.title || "(no title)"} — ${cur.artist || "(unknown artist)"}`;
    b = cur.state === "searching" ? "Searching Soulseek…" : `Downloading from ${cur.user} · ${(lib + c.failed + 1).toLocaleString()} of ${c.n.toLocaleString()}`;
  } else if (!can.ok) { a = can.why; b = !current ? "Your playlists will show up on the left." : $("#user").value.trim() ? "" : "No account? Just make one up."; }
  else if (finished) {
    if (c.failed === c.n) { a = "Nothing was found"; b = "Check your Soulseek login and internet connection. Details shows what happened."; }
    else if (c.done === 0 && c.failed === 0) { a = "Nothing new to download"; b = `All ${c.n.toLocaleString()} songs are already in your library.`; }
    else if (c.failed) { a = `Finished: ${lib.toLocaleString()} of ${c.n.toLocaleString()} in your library`; b = `${c.failed.toLocaleString()} couldn't be found. Press Retry to search harder.`; }
    else { a = `Finished: all ${c.n.toLocaleString()} in your library`; b = "Everything was found."; }
  } else if (lib + c.failed > 0 && c.queued) { a = `Stopped: ${lib.toLocaleString()} of ${c.n.toLocaleString()} done`; b = "Press Download to continue."; }
  else { a = "Ready"; b = "Press Download to start."; }
  t1.textContent = a; t1.title = a;
  t2.textContent = b || "\u00a0"; // keep the line so the top bar never changes height
}

function renderPlaylists() {
  const list = $("#playlistList");
  const key = playlists.map((p) => `${p.name}|${p.done}|${p.total}|${p === current}`).join("\n");
  if (list.dataset.key === key) return;
  list.dataset.key = key;
  list.innerHTML = playlists.map((p, i) => {
    const pct = p.total ? (Math.min(p.done, p.total) / p.total) * 100 : 0;
    return `<li class="${p === current ? "sel" : ""}" role="option" tabindex="0" aria-selected="${p === current}" data-idx="${i}" title="${esc(p.name)}">
      <span class="pl-name" dir="auto">${esc(p.name)}</span>
      <span class="pl-count">${p.done.toLocaleString()}/${p.total.toLocaleString()}</span>
      <span class="pl-meter"><span style="width:${pct}%"></span></span>
    </li>`;
  }).join("") || `<li class="pl-empty">Nothing here yet</li>`;
}

function followCurrent() {
  if (!running || Date.now() - lastUserScroll < 3000) return;
  const cur = current.tracks.find((t) => t.state === "downloading" || t.state === "searching");
  if (cur && cur.el) cur.el.scrollIntoView({ block: "nearest" });
}

function log(bold, rest = "") {
  const atBottom = logEl.scrollHeight - logEl.scrollTop - logEl.clientHeight < 30;
  const line = document.createElement("span");
  const b = document.createElement("b");
  b.textContent = bold;
  line.append(`${new Date().toTimeString().slice(0, 8)}  `, b, `${rest}\n`);
  logEl.append(line);
  while (logEl.childNodes.length > 2000) logEl.firstChild.remove();
  if (atBottom) logEl.scrollTop = logEl.scrollHeight;
}

function setPath(full) {
  const el = $("#folderPath");
  el.title = full;
  const parts = full.split("/");
  el.textContent = full.length > 32 && parts.length > 3 ? `…/${parts.slice(-2).join("/")}` : full;
}

/* ================= controls ================= */

$("#goBtn").addEventListener("click", () => (running ? stop() : start()));
$("#retryBtn").addEventListener("click", retry);
["#user", "#pass"].forEach((id) => $(id).addEventListener("input", renderAll));
$(".track-table").addEventListener("wheel", () => (lastUserScroll = Date.now()), { passive: true });
$(".track-table").addEventListener("mousedown", () => (lastUserScroll = Date.now()));

$("#playlistList").addEventListener("click", (e) => {
  const li = e.target.closest("li[data-idx]");
  if (li) selectPlaylist(+li.dataset.idx);
});
$("#playlistList").addEventListener("keydown", (e) => {
  const li = e.target.closest("li[data-idx]");
  if (!li) return;
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); const idx = li.dataset.idx; selectPlaylist(+idx); $(`#playlistList li[data-idx="${idx}"]`)?.focus(); }
  if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); (e.key === "ArrowDown" ? li.nextElementSibling : li.previousElementSibling)?.focus(); }
});

// segmented controls behave like radio groups
document.querySelectorAll(".seg").forEach((seg) => {
  const btns = [...seg.querySelectorAll("button")];
  const choose = (b) => btns.forEach((x) => { const on = x === b; x.classList.toggle("on", on); x.setAttribute("aria-checked", on); x.tabIndex = on ? 0 : -1; });
  btns.forEach((b) => b.setAttribute("role", "radio"));
  choose(btns.find((b) => b.classList.contains("on")) || btns[0]);
  seg.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { choose(b); updateFmtHint(); } });
  seg.addEventListener("keydown", (e) => {
    const i = btns.indexOf(document.activeElement);
    if (i < 0 || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return;
    e.preventDefault();
    const n = btns[(i + (e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : btns.length - 1)) % btns.length];
    choose(n); n.focus(); updateFmtHint();
  });
});

$("#toggleTerm").addEventListener("click", () => {
  const hidden = $(".app").classList.toggle("term-hidden");
  $("#toggleTerm").textContent = hidden ? "Show" : "Hide";
});

// drag the splitter to resize the details pane; always leave room for the song list
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

// real native folder picker when running inside the app window
$("#chooseFolder").addEventListener("click", async () => {
  if (!window.pywebview?.api?.choose_folder) return alert("The folder picker works in the app window.");
  const path = await window.pywebview.api.choose_folder();
  if (path) setPath(path);
});
$("#getPlaylist").addEventListener("click", () => alert("In the real app: opens Exportify in your browser, with a short how-to."));
$("#addCsv").addEventListener("click", () => alert("In the real app: opens a file picker for your Exportify CSV."));

/* ---- format hint follows the choices ---- */
function updateFmtHint() {
  const fmt = $("#fmtSeg .on").textContent, other = fmt === "MP3" ? "FLAC" : "MP3";
  const force = $("#modeSeg .on").textContent === "Force";
  $("#fmtHint").textContent = force ? `Only ${fmt}. Missing songs get offered as ${other}.` : `${fmt} if possible, otherwise anything.`;
}
updateFmtHint();

/* ---- sheets: one at a time, focus moves in and comes back ---- */
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
  returnFocus?.focus?.();
}
$("#openAdvanced").addEventListener("click", () => openSheet("#advancedSheet"));
$("#openSettings").addEventListener("click", () => openSheet("#settingsSheet"));
document.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", closeSheets));
document.querySelectorAll(".sheet-backdrop").forEach((bd) => bd.addEventListener("click", (e) => { if (e.target === bd) closeSheets(); }));
$("#restoreDefaults").addEventListener("click", () => {
  $("#advancedSheet").querySelectorAll("input[type=text]").forEach((i) => (i.value = ""));
  $("#advancedSheet").querySelectorAll("input[type=checkbox]").forEach((i) => (i.checked = false));
});
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

/* ---- looks ---- */
const LOOKS = ["phosphor", "jukebox"];
function setLook(look) {
  if (!LOOKS.includes(look)) look = LOOKS[0];
  document.body.dataset.theme = look;
  document.querySelectorAll(".look-card").forEach((c) => c.classList.toggle("on", c.dataset.look === look));
  try { localStorage.setItem("unspootify.look", look); } catch {}
}
document.querySelectorAll(".look-card").forEach((c) => c.addEventListener("click", () => setLook(c.dataset.look)));

/* ---- test-data picker (mockup only) ---- */
const pick = $("#scenarioPick");
pick.innerHTML = Object.entries(SCENARIOS).map(([k, s]) => `<option value="${k}">${esc(s.label)}</option>`).join("");
pick.addEventListener("change", () => {
  loadScenario(pick.value);
  try { localStorage.setItem("unspootify.scenario", pick.value); } catch {}
});

/* ---- boot ---- */
const params = new URLSearchParams(location.search);
let saved = {};
try { saved = { look: localStorage.getItem("unspootify.look"), scn: localStorage.getItem("unspootify.scenario") }; } catch {}
setLook(params.get("theme") || saved.look || "phosphor");
const firstScn = params.get("scn") || saved.scn || "normal";
pick.value = SCENARIOS[firstScn] ? firstScn : "normal";
loadScenario(pick.value);
if (params.get("sheet")) openSheet(`#${params.get("sheet")}Sheet`);
if (params.has("still")) { start(); for (let k = 0; k < 14 && running; k++) tick(); if (running) { clearInterval(timer); timer = null; } renderAll(); }
