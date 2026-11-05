// Drives the app in headless Chromium and fails on any CSP violation. See scripts/csp_browser_check.sh.
import { chromium } from "playwright";
import fs from "node:fs";

const BASE = process.env.BASE, API = process.env.API, OUT = process.env.OUT || ".";
const violations = [], consoleErrors = [], notes = [];
let step = "init";
const note = (m) => { notes.push(`[${step}] ${m}`); console.log(`[${step}] ${m}`); };

const browser = await chromium.launch({
  channel: "chromium", // new-headless full Chromium (the headless shell ignores the secure-origin flag)
  // http://web is not a secure context, so getUserMedia/MediaRecorder would be hidden without this flag.
  args: ["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream", `--unsafely-treat-insecure-origin-as-secure=${BASE}`],
});
const ctx = await browser.newContext({ permissions: ["microphone"], viewport: { width: 1100, height: 900 } });
// Record securitypolicyviolation in every document (pages, iframes) and report via console marker.
await ctx.addInitScript(() => {
  const rep = (e) => console.error("__CSPV__" + JSON.stringify({
    directive: e.effectiveDirective, blocked: e.blockedURI, doc: e.documentURI, src: e.sourceFile, line: e.lineNumber, disp: e.disposition,
  }));
  self.addEventListener("securitypolicyviolation", rep);
});
const page = await ctx.newPage();
const seen = new Set();
const onConsole = (m) => {
  const t = m.text();
  if (t.startsWith("__CSPV__")) { const k = t; if (!seen.has(k)) { seen.add(k); violations.push({ step, ...JSON.parse(t.slice(8)) }); } return; }
  if (m.type() === "error") {
    if (/Content Security Policy|Refused to/i.test(t)) violations.push({ step, console: t });
    else consoleErrors.push({ step, text: t.slice(0, 300), url: m.location()?.url });
  }
};
page.on("console", onConsole);
page.on("pageerror", (e) => consoleErrors.push({ step, pageerror: String(e).slice(0, 300) }));
page.on("worker", (w) => note("worker started " + w.url()));
page.on("requestfailed", (r) => notes.push(`[${step}] requestfailed ${r.url().slice(0, 120)} ${r.failure()?.errorText}`));
const net = {};
page.on("response", (r) => {
  const u = new URL(r.url());
  if (u.host !== new URL(BASE).host && u.host !== new URL(API).host) {
    const k = `${u.host} ${r.status() < 400 ? "ok" : "http" + r.status()}`; net[k] = (net[k] || 0) + 1;
    if (/jsdelivr/.test(u.host)) note(`${r.status()} ${u.pathname.slice(0, 90)}`);
  }
});
page.on("response", (r) => { if (/\.(wasm|mjs)(\?|$)/.test(r.url())) note(`${r.status()} ${r.url().replace(/^https?:\/\/[^/]+/, (h) => h).slice(0, 110)}`); });
page.on("console", (m) => { if (step === "speaking" && m.type() !== "error") note("console." + m.type() + ": " + m.text().slice(0, 160)); });
page.on("request", (r) => { if (/sentry/.test(r.url())) note("sentry request " + new URL(r.url()).host); });
const cdp = await ctx.newCDPSession(page);
await cdp.send("Log.enable");
cdp.on("Log.entryAdded", ({ entry }) => {
  if (entry.source === "security" || /Content Security Policy/i.test(entry.text || ""))
    violations.push({ step, cdp: entry.text?.slice(0, 300), url: entry.url });
});

const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png` }).catch(() => {});
const settle = (ms = 800) => page.waitForTimeout(ms);
const email = `csp-${Date.now()}@example.com`, pw = "csp-check-pass-1";

async function api(path, token) {
  const r = await fetch(API + path, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  return r.json();
}

async function main() {
  step = "headers";
  const resp = await page.goto(BASE + "/register");
  const csp = resp.headers()["content-security-policy"];
  if (!csp) throw new Error("no enforcing Content-Security-Policy header");
  if (resp.headers()["content-security-policy-report-only"]) note("report-only header also present");

  step = "register";
  await page.fill("#reg-name", "CSP Check");
  await page.fill("#reg-email", email);
  await page.fill("#reg-password", pw);
  await page.click("button[type=submit]");
  await settle(2000); note("url " + page.url());
  if (/welcome/.test(page.url())) { await page.getByRole("button", { name: /skip for now/i }).click(); await settle(); }

  step = "login";
  await page.evaluate(() => localStorage.clear()); await ctx.clearCookies();
  await page.goto(BASE + "/login");
  await page.fill("#login-email", process.env.ADMIN_EMAIL);
  await page.fill("#login-password", process.env.ADMIN_PW);
  await page.click("button[type=submit]");
  await page.waitForFunction(() => !location.pathname.startsWith("/login"), null, { timeout: 15000 });
  await settle(1500);
  if (/welcome/.test(page.url())) { await page.getByRole("button", { name: /skip for now/i }).click(); await settle(); }
  note("logged in at " + page.url());

  const token = await page.evaluate(() => {
    for (const [, v] of Object.entries(localStorage)) if (/^eyJ/.test(v)) return v;
    for (const [, v] of Object.entries(localStorage)) { const m = /eyJ[\w-]+\.[\w-]+\.[\w-]+/.exec(v); if (m) return m[0]; }
  });
  const courses = await api("/courses", token);
  note("courses " + courses.map((c) => `${c.title}(${c.source_language}>${c.target_language})`).join("; "));
  const lessonsOf = async (cTitle) => {
    const c = courses.find((x) => x.title === cTitle); const out = [];
    for (const u of await api(`/courses/${c.id}/units`, token))
      for (const l of await api(`/units/${u.id}/lessons`, token)) out.push({ c, u, l });
    return out;
  };
  const fa = await lessonsOf("Farsi Foundations");
  const speak = fa.find((x) => x.l.title === "First conversation");
  const plain = fa[0];

  step = "lesson-audio";
  await page.goto(`${BASE}/lessons/${plain.l.id}`); await settle(2000);
  await playAudioAndAdvance(6);

  step = "speaking";
  await page.goto(`${BASE}/lessons/${speak.l.id}`); await settle(2000);
  await speakingExercise();

  step = "profile";
  await page.goto(BASE + "/profile"); await settle(1500); await shot("30-profile");
  await page.fill("#change-password-current", process.env.ADMIN_PW).catch(() => note("no change-password-current"));
  await page.fill("#change-password-new", "csp-new-pass-22").catch(() => {});
  await page.fill("#change-password-repeat", "csp-new-pass-22").catch(() => {});
  await page.getByRole("button", { name: /change password|update password|save/i }).last().click().catch((e) => note("pw submit: " + e.message.slice(0, 80)));
  await settle(1500); await shot("31-pw");

  // Sentry: SDK init ran at load (no violation so far); "Report a problem" makes it send an envelope to the DSN host.
  step = "sentry";
  await page.getByRole("button", { name: "Report a problem" }).click();
  await page.fill("#report-problem-message", "CSP browser check, ignore");
  const envelope = page.waitForRequest((r) => /ingest\.de\.sentry\.io/.test(r.url()), { timeout: 10000 }).catch(() => null);
  await page.getByRole("button", { name: "Send report" }).click();
  note(await envelope ? "sentry envelope request attempted (CSP allowed it)" : "WARN no sentry request seen (flush timeout or blocked)");
  await settle(3000); await shot("32-sentry");

  for (const [name, path] of [["privacy", "/privacy"], ["terms", "/terms"], ["home", "/"], ["review", "/review"], ["practice", "/practice"], ["vocab", "/vocabulary"], ["showcase", "/showcase"], ["404", "/nope"]]) {
    step = name; await page.goto(BASE + path); await settle(1200); await shot("40-" + name);
  }

  step = "rtl";
  await page.goto(`${BASE}/courses/${plain.c.id}`); await settle(1500); await shot("50-rtl-course");
  await page.goto(`${BASE}/units/${plain.u.id}`); await settle(1500); await shot("51-rtl-unit");
  // UI language Persian (RTL chrome), then run a Farsi lesson in it.
  const sel = page.locator("select").first();
  if (await sel.count()) { await sel.selectOption("fa").catch((e) => note("lang select: " + e.message.slice(0, 80))); await settle(2000); }
  note("html dir=" + (await page.evaluate(() => document.documentElement.dir)));
  await page.goto(`${BASE}/lessons/${plain.l.id}`); await settle(2000); await shot("52-rtl-lesson");
  await playAudioAndAdvance(6);
  await page.goto(BASE + "/profile"); await settle(1500); await shot("53-rtl-profile");
}

async function visibleButtons() {
  return page.locator("button:visible").evaluateAll((els) => els.map((e) => (e.getAttribute("aria-label") || e.textContent || "").trim()));
}

// Play any audio buttons, answer or advance through exercises with generic heuristics.
async function playAudioAndAdvance(max) {
  for (let i = 0; i < max; i++) {
    const play = page.locator('button.speak-button:visible, button[aria-label="Play audio"]:visible').first();
    if (await play.count()) { await play.click().catch(() => {}); await settle(1500); }
    const btns = await visibleButtons();
    note(`iter ${i} ${page.url().replace(BASE, "")} ${JSON.stringify(btns.map((b) => b.slice(0, 25)))}`);
    await shot(`10-${step}-${i}`);
    await advance();
  }
}

async function advance() {
  const tryClick = async (loc) => { if (await loc.count()) { await loc.first().click({ timeout: 2000 }).catch(() => {}); await settle(700); return true; } return false; };
  for (const re of [/^(continue|next|got it|start|ok)/i]) if (await tryClick(page.getByRole("button", { name: re }))) return;
  if (!/^[\x00-\x7f]*$/.test((await visibleButtons()).join(""))) { if (await tryClick(page.locator("button.btn:visible:not([disabled])"))) return; }
  // answer: pick first option-like control, type into text input, or check
  await tryClick(page.getByRole("button", { name: /use my keyboard instead/i }));
  const input = page.locator('input[type=text]:visible, textarea:visible').first();
  if (await input.count()) await input.fill("salam").catch(() => {});
  else await tryClick(page.locator(".choice:visible, .option:visible, button.choice-option:visible, [role=radio]:visible, .word-bank button:visible, .word-chip:visible"));
  await tryClick(page.getByRole("button", { name: /^(check|submit|respond)/i }));
  await tryClick(page.getByRole("button", { name: /^(continue|next|got it|finish)/i }));
  // Non-English UI: fall back to the primary action button.
  await tryClick(page.locator("button.btn-block:visible:not([disabled])"));
}

async function speakingExercise() {
  for (let i = 0; i < 8; i++) {
    const toggle = page.getByRole("button", { name: "Speak instead" });
    if (await toggle.count()) {
      await toggle.click(); await settle(500);
      await page.getByRole("button", { name: /tap to speak/i }).click();
      await settle(3000); await shot("20-recording");
      await page.getByRole("button", { name: /tap to stop/i }).click();
      note("recording stopped; waiting for transcription (model download)");
      // Poll until the "Transcribing…" state is gone (model download can take minutes).
      const t0 = Date.now(); let gone = 0;
      while (Date.now() - t0 < 300000 && gone < 3) {
        gone = (await page.getByText(/transcribing/i).count()) === 0 ? gone + 1 : 0;
        await settle(1000);
      }
      note(`transcription state cleared after ${Math.round((Date.now() - t0) / 1000)}s`);
      await settle(1500); await shot("21-transcribed");
      note("input after transcription: " + JSON.stringify(await page.locator("input[type=text]").first().inputValue().catch(() => null)));
      return;
    }
    note(`speak iter ${i} ${JSON.stringify((await visibleButtons()).map((b) => b.slice(0, 25)))}`);
    await shot(`19-speak-${i}`);
    await advance();
  }
  note("no speaking exercise reached");
}

try { await main(); } catch (e) { consoleErrors.push({ step, fatal: String(e.stack || e).slice(0, 500) }); console.error(e); }
console.log("external hosts contacted:", JSON.stringify(net));
const report = { net, violations, consoleErrors, notes, ok: violations.length === 0 && !consoleErrors.some((e) => e.fatal) };
fs.writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 1));
console.log(JSON.stringify({ violations, consoleErrors: consoleErrors.slice(0, 15) }, null, 1));
await browser.close();
process.exit(report.ok ? 0 : 1);
