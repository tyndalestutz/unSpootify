// Tiny UI test harness. Prepended to each scenario script by tests/test_ui.py.
const T = {
  sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
  $: (s) => document.querySelector(s),
  async waitFor(fn, ms = 20000, what = "condition") {
    const end = Date.now() + ms;
    while (Date.now() < end) { try { if (fn()) return true; } catch {} await T.sleep(50); }
    throw new Error(`timed out waiting for ${what}`);
  },
  click(sel) { const el = T.$(sel); if (!el) throw new Error(`no ${sel}`); el.click(); },
  type(sel, text) { const el = T.$(sel); el.value = text; el.dispatchEvent(new Event("input", { bubbles: true })); el.dispatchEvent(new Event("change", { bubbles: true })); },
  check(name, ok, detail = "") {
    const line = `CHECK ${ok ? "PASS" : "FAIL"} ${name}${ok ? "" : ": " + detail}`;
    console.log(line);
    (window.__checkLog = window.__checkLog || []).push(line);
  },
  visible(sel) { const el = T.$(sel); return !!el && !el.hidden && el.offsetParent !== null; },
  text(sel) { return (T.$(sel)?.textContent || "").trim(); },
  async run(steps) {
    await T.waitFor(() => window.unspootifyReady, 10000, "app ready");
    for (const [name, fn] of steps) {
      try { await fn(); } catch (e) { T.check(name, false, String(e && e.message || e)); }
    }
    console.log("CHECK DONE");
    (window.__checkLog = window.__checkLog || []).push("CHECK DONE");
  },
};
