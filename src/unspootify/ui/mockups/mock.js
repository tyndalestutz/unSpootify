// Look-check mockup: fake data + simulated downloads. Nothing here talks to sockseek.

const TRACKS = [
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

const PLAYLISTS = [
  { name: "road trip '03", total: 18, done: 0 },
  { name: "liked songs", total: 412, done: 251 },
  { name: "sunday morning", total: 24, done: 24 },
  { name: "gym (don't judge)", total: 37, done: 0 },
];

const USERS = ["vinylghost", "flac_attack", "mp3dad99", "lowendtheory", "sk8_or_die", "crate_digger"];
const LABEL = { queued: "Waiting", searching: "Searching…", downloading: "", done: "Done", skipped: "Already have", failed: "Not found" };

const $ = (s) => document.querySelector(s);
const rowsEl = $("#trackRows");
const logEl = $("#log");
let tracks, running = false, timer = null;

function reset() {
  tracks = TRACKS.map(([title, artist, album], i) => ({
    i: i + 1, title, artist, album, state: "queued", pct: 0, fmt: "", wait: 0,
    willFail: i === 7 || i === 13, have: i === 2,
  }));
  // start mid-run so the screen has something to show
  for (let k = 0; k < 4; k++) finish(tracks[k], true);
  logEl.textContent = "";
  log(`<b>sockseek 3.0.6</b> · logged in as ipod_dreamer`);
  log(`Loaded playlist "road trip '03" (18 tracks)`);
  render();
}

function finish(t, quiet) {
  if (t.have) { t.state = "skipped"; t.fmt = "MP3"; t.pct = 100; if (!quiet) log(`Skipping (already in library): ${t.artist} - ${t.title}`); return; }
  if (t.willFail) { t.state = "failed"; t.pct = 0; if (!quiet) log(`<b>Not found:</b> ${t.artist} - ${t.title}`); return; }
  t.state = "done"; t.pct = 100; t.fmt = t.fmt || (Math.random() < 0.8 ? "MP3" : "FLAC");
  if (!quiet) log(`<b>Succeeded:</b> ${t.artist}/${t.album} [${t.fmt}]/${String(t.i).padStart(2, "0")}. ${t.title}.${t.fmt.toLowerCase()}`);
}

function tick() {
  const active = tracks.filter((t) => t.state === "searching" || t.state === "downloading");
  while (active.length < 2) {
    const next = tracks.find((t) => t.state === "queued");
    if (!next) break;
    if (next.have) { finish(next); continue; }
    next.state = "searching"; next.wait = 4 + Math.floor(Math.random() * 6);
    log(`Searching: ${next.artist} - ${next.title}`);
    active.push(next);
  }
  for (const t of active) {
    if (t.state === "searching" && --t.wait <= 0) {
      if (t.willFail) { finish(t); continue; }
      const u = USERS[Math.floor(Math.random() * USERS.length)];
      t.fmt = Math.random() < 0.8 ? "MP3" : "FLAC";
      t.user = u;
      t.state = "downloading";
      log(`Found ${20 + Math.floor(Math.random() * 60)} results · best: ${u}  ${t.fmt === "MP3" ? "320kbps" : "16bit/44.1kHz"}  .${t.fmt.toLowerCase()}`);
    } else if (t.state === "downloading") {
      t.pct = Math.min(100, t.pct + 3 + Math.random() * 8);
      if (t.pct >= 100) finish(t);
    }
  }
  render();
  if (!tracks.some((t) => ["queued", "searching", "downloading"].includes(t.state))) {
    stop(true);
    setTimeout(() => { reset(); start(); }, 5000);
  }
}

function start() { running = true; $("#goBtn").textContent = "Stop"; $("#goBtn").classList.add("running"); timer = setInterval(tick, 220); }
function stop(finished) {
  running = false; clearInterval(timer);
  $("#goBtn").textContent = "Download"; $("#goBtn").classList.remove("running");
  if (!finished) log("Stopped.");
  render(finished);
}

function asciiBar(p) { const n = Math.round(p / 100 * 12); return "[" + "#".repeat(n) + ".".repeat(12 - n) + "]"; }

function render(finished) {
  rowsEl.innerHTML = tracks.map((t) => {
    const busy = t.state === "searching" || t.state === "downloading";
    const label = t.state === "downloading" ? `${Math.floor(t.pct)}%` : LABEL[t.state];
    const showBar = t.state === "downloading";
    return `<div class="track-row ${busy ? "active" : ""}">
      <span class="c-num">${t.i}</span>
      <span class="c-title">${t.title}</span>
      <span class="c-artist">${t.artist}</span>
      <span class="c-album">${t.album}</span>
      <span class="c-fmt">${t.fmt ? `<span>${t.fmt}</span>` : ""}</span>
      <span class="c-status st-${t.state}">
        <span class="st-text">${label}</span>
        ${showBar ? `<span class="bar"><i style="width:${t.pct}%"></i></span><span class="asciibar">${asciiBar(t.pct)}</span>` : ""}
      </span>
    </div>`;
  }).join("");

  const c = (s) => tracks.filter((t) => t.state === s).length;
  const done = c("done"), failed = c("failed"), skipped = c("skipped");
  $("#counts").textContent = `18 songs · ${done} downloaded · ${skipped} already had · ${failed} not found`;

  const finishedCount = done + failed + skipped;
  PLAYLISTS[0].done = done + skipped;
  $("#lcdFill").style.width = `${(finishedCount / tracks.length) * 100}%`;
  const cur = tracks.find((t) => t.state === "downloading") || tracks.find((t) => t.state === "searching");
  if (finished) {
    $("#lcdTitle").textContent = `Finished: ${done + skipped} of 18 in your library`;
    $("#lcdSub").textContent = failed ? `${failed} couldn't be found. Try again with "Try harder"?` : "Everything found.";
  } else if (cur && running) {
    $("#lcdTitle").textContent = `${cur.title} — ${cur.artist}`;
    $("#lcdSub").textContent = cur.state === "searching" ? "Searching Soulseek…" : `Downloading from ${cur.user} · ${finishedCount + 1} of 18`;
  } else {
    $("#lcdTitle").textContent = "Ready";
    $("#lcdSub").textContent = "Pick a playlist and hit Download";
  }
  renderPlaylists();
}

function renderPlaylists() {
  $("#playlistList").innerHTML = PLAYLISTS.map((p, i) => `
    <li class="${i === 0 ? "sel" : ""}">
      <span class="pl-name">${p.name}</span>
      <span class="pl-count">${p.done}/${p.total}</span>
      <span class="pl-meter"><span style="width:${(p.done / p.total) * 100}%"></span></span>
    </li>`).join("");
}

function log(html) {
  const atBottom = logEl.scrollHeight - logEl.scrollTop - logEl.clientHeight < 30;
  const time = new Date().toTimeString().slice(0, 8);
  logEl.insertAdjacentHTML("beforeend", `${time}  ${html}\n`);
  if (atBottom) logEl.scrollTop = logEl.scrollHeight;
}

/* ---- controls ---- */
$("#goBtn").addEventListener("click", () => (running ? stop() : start()));

document.querySelectorAll(".seg").forEach((seg) =>
  seg.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    seg.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
  })
);

$("#toggleTerm").addEventListener("click", () => {
  const hidden = $(".app").classList.toggle("term-hidden");
  $("#toggleTerm").textContent = hidden ? "Show" : "Hide";
});

// drag the splitter to resize the details pane
(() => {
  const app = $(".app"), split = $("#splitter");
  let dragging = false;
  split.addEventListener("mousedown", (e) => { dragging = true; e.preventDefault(); });
  window.addEventListener("mouseup", () => (dragging = false));
  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const h = Math.max(80, Math.min(window.innerHeight * 0.7, window.innerHeight - e.clientY - 12));
    app.style.setProperty("--term-h", `${h}px`);
  });
})();

// real native folder picker when running inside the app window
$("#chooseFolder").addEventListener("click", async () => {
  if (!window.pywebview?.api?.choose_folder) return alert("The folder picker works in the app window.");
  const path = await window.pywebview.api.choose_folder();
  if (path) $("#folderPath").textContent = path;
});
$("#getPlaylist").addEventListener("click", () => alert("In the real app: opens Exportify in your browser, with a short how-to."));
$("#addCsv").addEventListener("click", () => alert("In the real app: opens a file picker for your Exportify CSV."));

/* ---- look switcher ---- */
function pick(theme) {
  document.body.dataset.theme = theme;
  document.querySelectorAll(".switcher button").forEach((b) => b.classList.toggle("on", b.dataset.pick === theme));
  try { localStorage.setItem("mockTheme", theme); } catch {}
}
document.querySelectorAll(".switcher button").forEach((b) => b.addEventListener("click", () => pick(b.dataset.pick)));

const params = new URLSearchParams(location.search);
let saved = null;
try { saved = localStorage.getItem("mockTheme"); } catch {}
pick(params.get("theme") || saved || "phosphor");

reset();
if (params.get("still") === null) start();
else { start(); clearInterval(timer); for (let k = 0; k < 14; k++) tick(); }
