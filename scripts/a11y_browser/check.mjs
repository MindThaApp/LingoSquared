// Drives the app in headless Chromium and runs axe-core on every main page / state. See scripts/a11y_check.sh.
// Fails (exit 1) on any serious/critical violation; moderate/minor, small touch targets, missing focus
// indicators and 360px overflow are reported (report.json) but not fatal, except overflow/focus-lost which are listed as "issues".
import { chromium } from "playwright";
import fs from "node:fs";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const AXE_SRC = fs.readFileSync(require.resolve("axe-core/axe.min.js"), "utf8");
const BASE = process.env.BASE, API = process.env.API, OUT = process.env.OUT || ".";
const CONFIGS = [
  { name: "desktop-light", viewport: { width: 1100, height: 900 }, scheme: "light" },
  { name: "desktop-dark", viewport: { width: 1100, height: 900 }, scheme: "dark" },
  { name: "mobile360-dark", viewport: { width: 360, height: 740 }, scheme: "dark", isMobile: true, hasTouch: true },
];
const ONLY = process.env.A11Y_ONLY; // optional: substring filter on config name

const findings = new Map(); // key -> {id, impact, help, nodes:Set, pages:Set}
const issues = [];          // non-axe issues (overflow, focus, targets, state copy)
const notes = [];
let cfgName = "", label = "";
const note = (m) => { notes.push(`[${cfgName}/${label}] ${m}`); console.log(`[${cfgName}/${label}] ${m}`); };

const browser = await chromium.launch({ channel: "chromium", args: [
  "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
  // The stack is plain http://web: treat it as a secure context so getUserMedia / MediaRecorder exist and the mic UI renders.
  "--unsafely-treat-insecure-origin-as-secure=http://web",
] });

async function api(path, token, init = {}) {
  const r = await fetch(API + path, { ...init, headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), "Content-Type": "application/json" } });
  return r.json();
}
async function register(email, pw, name) {
  return api("/auth/register", null, { method: "POST", body: JSON.stringify({ email, password: pw, display_name: name }) });
}

async function runAxe(page, tag) {
  const pageLabel = `${cfgName}/${label}${tag ? "/" + tag : ""}`;
  try {
    await page.evaluate(AXE_SRC);
    const res = await page.evaluate(() => window.axe.run(document, {
      runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] }, resultTypes: ["violations"],
    }));
    for (const v of res.violations) {
      const k = `${v.id}|${v.nodes.map((n) => n.target.join(" ")).sort()[0]}`;
      let f = findings.get(v.id);
      if (!f) { f = { id: v.id, impact: v.impact, help: v.help, nodes: new Set(), pages: new Set() }; findings.set(v.id, f); }
      for (const n of v.nodes) f.nodes.add(n.target.join(" ") + (n.any[0]?.data && v.id === "color-contrast" ? ` [${n.any[0].data.fgColor} on ${n.any[0].data.bgColor} ${n.any[0].data.contrastRatio}] ${n.html.slice(0, 90)}` : ""));
      f.pages.add(pageLabel);
      void k;
    }
    if (res.violations.length) note(`axe: ${res.violations.map((v) => `${v.id}(${v.impact},${v.nodes.length})`).join(" ")}`);
  } catch (e) { issues.push({ page: pageLabel, kind: "axe-error", detail: String(e).slice(0, 200) }); }
}

async function layoutChecks(page, tag) {
  const pageLabel = `${cfgName}/${label}${tag ? "/" + tag : ""}`;
  const r = await page.evaluate(() => {
    const overflow = document.documentElement.scrollWidth - window.innerWidth;
    const small = [];
    for (const el of document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, [role=button], [role=radio], [role=tab]')) {
      const b = el.getBoundingClientRect();
      if (!b.width || !b.height) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === "hidden" || cs.display === "none") continue;
      if (el.tagName === "A" && el.closest("p, li, span, .legal, article") && getComputedStyle(el).display === "inline") continue; // inline text links exempt (WCAG 2.5.8)
      if (b.width < 24 || b.height < 24) small.push(`${el.tagName.toLowerCase()}${el.id ? "#" + el.id : ""}.${(el.className?.toString?.() || "").split(" ")[0]} ${Math.round(b.width)}x${Math.round(b.height)} "${(el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 24)}"`);
    }
    return { overflow, small };
  });
  if (r.overflow > 1) issues.push({ page: pageLabel, kind: "horizontal-overflow", detail: `${r.overflow}px` });
  for (const s of r.small) issues.push({ page: pageLabel, kind: "small-target(<24px)", detail: s });
}

// Tab through the page: every focused element must show an indicator, focus must never fall to <body> mid-page.
async function tabAudit(page, n = 14, tag = "keyboard") {
  const pageLabel = `${cfgName}/${label}/${tag}`;
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  for (let i = 0; i < n; i++) {
    await page.keyboard.press("Tab");
    const info = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return { body: true };
      const cs = getComputedStyle(el);
      const outline = cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0;
      const shadow = cs.boxShadow && cs.boxShadow !== "none";
      return { desc: `${el.tagName.toLowerCase()}${el.id ? "#" + el.id : ""} "${(el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 24)}"`, visible: outline || shadow || el.matches(":focus-visible") && cs.outlineStyle !== "none" };
    });
    if (info.body) break; // end of the page's tab order: focus leaves to browser chrome (expected)
    if (!info.visible) issues.push({ page: pageLabel, kind: "no-visible-focus", detail: info.desc });
  }
}

// Audio and mic are stubbed: TTS / recorded clips answer with an empty 204, the STT endpoint with a fixed transcript,
// and the browser's fake capture device stands in for the microphone (see launch args). The wasm Whisper worker is
// disabled so the app falls back to the stubbed server transcription instead of downloading a model.
async function stubAudio(ctx) {
  await ctx.addInitScript(() => { window.Worker = undefined; });
  await ctx.route((u) => /\/(tts|media)(\/|$)|\/media\/audio\//.test(u.pathname), (r) => r.fulfill({ status: 204, body: "" }));
  await ctx.route((u) => u.pathname === "/stt/transcribe", (r) => r.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({ transcript: "مرحبا", words: [{ word: "مرحبا", start: 0, end: 0.6, probability: 0.92 }] }),
  }));
}

// Mic flow on a speak_repeat / speak_response step: voice mode, recording (level meter), transcribing, result.
async function micAudit(page) {
  const voiceToggle = page.getByRole("button", { name: /speak instead/i });
  if (!(await voiceToggle.count())) { issues.push({ page: `${cfgName}/${label}`, kind: "mic-ui-missing", detail: "no voice toggle on a speaking exercise" }); return; }
  await voiceToggle.first().click(); await settle(page, 400);
  await runAxe(page, "mic-voice-mode"); await layoutChecks(page, "mic-voice-mode");
  await page.screenshot({ path: `${OUT}/${cfgName}-${label}-mic-voice.png` }).catch(() => {});
  await page.getByRole("button", { name: /tap to speak/i }).first().click(); await settle(page, 700);
  await runAxe(page, "mic-recording"); await layoutChecks(page, "mic-recording");
  await page.screenshot({ path: `${OUT}/${cfgName}-${label}-mic-recording.png` }).catch(() => {});
  await page.getByRole("button", { name: /tap to stop/i }).first().click().catch(() => {});
  await settle(page, 1500);
  await runAxe(page, "mic-result"); await layoutChecks(page, "mic-result");
  await page.screenshot({ path: `${OUT}/${cfgName}-${label}-mic-result.png` }).catch(() => {});
  const typeToggle = page.getByRole("button", { name: /type instead/i });
  if (await typeToggle.count()) { await typeToggle.first().click(); await settle(page, 300); }
}

const settle = (page, ms = 700) => page.waitForTimeout(ms);
async function visit(page, path, name, { keyboard = false } = {}) {
  label = name;
  await page.goto(BASE + path, { waitUntil: "load" }); await settle(page, 1200);
  await runAxe(page); await layoutChecks(page);
  if (keyboard) await tabAudit(page);
  await page.screenshot({ path: `${OUT}/${cfgName}-${name}.png` }).catch(() => {});
}

// Advance one lesson screen: returns false when nothing actionable remains.
async function advance(page) {
  const tryClick = async (loc) => { if (await loc.count()) { await loc.first().click({ timeout: 2500 }).catch(() => {}); await settle(page, 500); return true; } return false; };
  const btn = (re) => page.getByRole("button", { name: re });
  if (await tryClick(btn(/^(continue|next|got it|start|ok|finish|done)/i).filter({ hasNotText: /^$/ }))) { return true; }
  const input = page.locator("input[type=text]:visible, textarea:visible").first();
  if (await input.count()) await input.fill("x").catch(() => {});
  else {
    // matching pairs: pair each left with right tile by index; otherwise pick first option / word chip.
    const lefts = page.locator('.matching-item[aria-pressed]');
    if (await lefts.count()) {
      for (let i = 0; i < 8; i++) {
        const l = page.locator('.matching-item[aria-pressed="false"]:not(.matched):not([disabled])').first();
        if (!(await l.count())) break;
        await l.click().catch(() => {});
        await page.locator(".matching-item:not([aria-pressed]):not(.matched):not([disabled])").first().click().catch(() => {});
      }
    } else await tryClick(page.locator("[role=radio]:visible:not([disabled]), .choice:visible:not([disabled]), .choice-option:visible:not([disabled]), .word-bank button:visible:not([disabled]), .word-chip:visible:not([disabled])"));
  }
  if (await tryClick(btn(/^(check|submit|respond)/i))) return true;
  return await tryClick(page.locator("button.btn-block:visible:not([disabled])"));
}

async function lessonWalk(page, lessonId, name, maxSteps = 16) {
  label = name;
  let micDone = false;
  await page.goto(`${BASE}/lessons/${lessonId}`); await settle(page, 1500);
  const seen = new Set();
  for (let i = 0; i < maxSteps; i++) {
    const sig = (await page.locator("main").innerText().catch(() => "")).slice(0, 80) + (await page.locator("button:visible").allInnerTexts().then((a) => a.join("|")).catch(() => ""));
    if (!seen.has(sig)) {
      seen.add(sig);
      await runAxe(page, `step${i}`); await layoutChecks(page, `step${i}`);
      if (i === 1) await tabAudit(page, 12, "keyboard-step1");
      if (!micDone && (await page.locator(".voice-capture").count())) { micDone = true; await micAudit(page); }
      await page.screenshot({ path: `${OUT}/${cfgName}-${name}-step${i}.png` }).catch(() => {});
    }
    if (/\/lessons\/[^/]+\/done/.test(page.url())) break;
    // After an answer, also audit the feedback state (advance() clicks Check; audit once more before Continue).
    if (!(await advance(page))) break;
    if (await page.locator("[role=alert], .feedback-banner").count()) { await runAxe(page, `feedback${i}`); }
  }
  await settle(page, 1000);
  if (/\/done/.test(page.url())) { label = name + "-done"; await runAxe(page); await layoutChecks(page); }
}

async function main() {
  const stamp = Date.now();
  const adminEmail = process.env.ADMIN_EMAIL, adminPw = process.env.ADMIN_PW;
  for (const cfg of CONFIGS) {
    if (ONLY && !cfg.name.includes(ONLY)) continue;
    cfgName = cfg.name;
    const ctx = await browser.newContext({ viewport: cfg.viewport, colorScheme: cfg.scheme, isMobile: cfg.isMobile, hasTouch: cfg.hasTouch, bypassCSP: true });
    await stubAudio(ctx);
    const page = await ctx.newPage();
    page.on("pageerror", (e) => issues.push({ page: `${cfgName}/${label}`, kind: "pageerror", detail: String(e).slice(0, 200) }));

    // ---- logged out
    for (const [p, n] of [["/", "landing"], ["/login", "login"], ["/register", "register"], ["/privacy", "privacy"], ["/terms", "terms"], ["/nope", "404"]]) await visit(page, p, n, { keyboard: n === "login" || n === "register" });
    // form errors
    label = "login-error"; await page.goto(BASE + "/login"); await page.fill("#login-email", "nobody@example.com"); await page.fill("#login-password", "wrong-password-1"); await page.click("button[type=submit]"); await settle(page, 1500); await runAxe(page);
    if (!(await page.locator("[role=alert]").count())) issues.push({ page: `${cfgName}/login-error`, kind: "error-not-announced", detail: "no role=alert after failed login" });
    label = "register-invalid"; await page.goto(BASE + "/register"); await page.fill("#reg-email", "not-an-email"); await page.fill("#reg-password", "x"); await page.click("button[type=submit]"); await settle(page, 800); await runAxe(page);

    // ---- new user: register through the UI -> onboarding
    const email = `a11y-${cfg.name}-${stamp}@example.com`, pw = "a11y-check-pass-1";
    label = "register-flow"; await page.goto(BASE + "/register");
    await page.fill("#reg-name", "A11y Check"); await page.fill("#reg-email", email); await page.fill("#reg-password", pw);
    await page.click("button[type=submit]"); await settle(page, 2500);
    note("after register: " + page.url().replace(BASE, ""));
    if (/welcome/.test(page.url())) { label = "onboarding"; await runAxe(page); await layoutChecks(page); await tabAudit(page, 10); await page.screenshot({ path: `${OUT}/${cfgName}-onboarding.png` }).catch(() => {}); }
    await visit(page, "/welcome", "onboarding-direct");
    // Onboarding skip so later routes are reachable.
    const skip = page.getByRole("button", { name: /skip/i }); if (await skip.count()) { await skip.first().click().catch(() => {}); await settle(page, 800); }

    // ---- main authed pages (new user, empty states)
    for (const [p, n] of [["/", "home-empty"], ["/courses", "courses"], ["/review", "review-empty"], ["/practice", "practice"], ["/vocabulary", "vocab"], ["/profile", "profile"], ["/showcase", "showcase"]]) await visit(page, p, n, { keyboard: n === "courses" || n === "profile" });

    // ---- courses -> units -> lessons, via API discovery with the user's token
    const token = await page.evaluate(() => { for (const [, v] of Object.entries(localStorage)) { const m = /eyJ[\w-]+\.[\w-]+\.[\w-]+/.exec(v); if (m) return m[0]; } });
    const courses = await api("/courses", token);
    note("courses: " + courses.map((c) => c.title).join("; "));
    const lessonsOf = async (c) => { const out = []; for (const u of await api(`/courses/${c.id}/units`, token)) for (const l of await api(`/units/${u.id}/lessons`, token)) out.push({ u, l }); return out; };
    for (const c of courses) {
      const rtl = ["ar", "fa", "prs"].includes(c.target_language);
      const tag = `${c.title.replace(/\W+/g, "-").toLowerCase()}`;
      await visit(page, `/courses/${c.id}`, `course-${tag}`);
      const ls = await lessonsOf(c);
      if (ls[0]) await visit(page, `/units/${ls[0].u.id}`, `unit-${tag}`);
      // Non-admin learners may be gated; try each lesson, stop at the first few that open.
      for (const { l } of ls.slice(0, 3)) await lessonWalk(page, l.id, `lesson-${tag}-${l.title.replace(/\W+/g, "-").toLowerCase().slice(0, 24)}`);
      void rtl;
    }

    // ---- after learning: review / home with data
    for (const [p, n] of [["/", "home-active"], ["/review", "review"], ["/vocabulary", "vocab-active"], ["/profile", "profile-active"]]) await visit(page, p, n);

    // ---- RTL UI (fa, ar): chrome mirrored + a lesson
    for (const lang of ["fa", "ar"]) {
      await page.evaluate((l) => localStorage.setItem("ui-language", l), lang);
      for (const [p, n] of [["/", `rtl-${lang}-home`], ["/courses", `rtl-${lang}-courses`], ["/profile", `rtl-${lang}-profile`]]) await visit(page, p, n);
      const c = courses.find((x) => x.target_language === "fa") || courses[0];
      const ls = await lessonsOf(c); if (ls[0]) await lessonWalk(page, ls[0].l.id, `rtl-${lang}-lesson`, 6);
      const dir = await page.evaluate(() => document.documentElement.dir); if (dir !== "rtl") issues.push({ page: `${cfgName}/rtl-${lang}`, kind: "dir-not-rtl", detail: dir });
    }
    await page.evaluate(() => localStorage.setItem("ui-language", "en"));

    // ---- error / offline states
    const apiHost = new URL(API).host;
    for (const [p, n] of [["/courses", "courses"], ["/review", "review"], ["/profile", "profile"], ["/vocabulary", "vocab"], ["/", "home"]]) {
      label = `err500-${n}`;
      await page.route((u) => u.host === apiHost && !u.pathname.startsWith("/auth"), (r) => r.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"boom"}' }));
      await page.goto(BASE + p); await settle(page, 9000);
      const txt = (await page.locator("main").innerText().catch(() => "")).trim();
      if (txt.length < 15 || /undefined|\[object|NaN|Traceback|boom/.test(txt)) issues.push({ page: `${cfgName}/${label}`, kind: "bad-error-state", detail: JSON.stringify(txt.slice(0, 120)) });
      if (n === "review" && !(await page.getByRole("button", { name: /back to home/i }).count())) issues.push({ page: `${cfgName}/${label}`, kind: "error-screen-no-way-back", detail: "review error state has no Back to home button" });
      await runAxe(page); await page.screenshot({ path: `${OUT}/${cfgName}-${label}.png` }).catch(() => {});
      await page.unrouteAll({ behavior: "ignoreErrors" }).catch(() => {});
      label = `offline-${n}`;
      await page.goto(BASE + p); await settle(page, 1500);
      await ctx.setOffline(true); await page.evaluate(() => window.dispatchEvent(new Event("offline")));
      await page.reload().catch(() => {}); // network error page expected for the document itself; use SPA nav instead
      await ctx.setOffline(false);
    }
    // Offline from within the SPA: load page, go offline, trigger refetch by navigating client-side.
    label = "offline-spa";
    await page.goto(BASE + "/"); await settle(page, 1500); await ctx.setOffline(true);
    await page.evaluate(() => { history.pushState({}, "", "/review"); window.dispatchEvent(new PopStateEvent("popstate")); }); await settle(page, 4000);
    const offTxt = (await page.locator("main").innerText().catch(() => "")).trim();
    if (offTxt.length < 15 || /undefined|\[object|NaN/.test(offTxt)) issues.push({ page: `${cfgName}/offline-spa`, kind: "bad-offline-state", detail: JSON.stringify(offTxt.slice(0, 120)) });
    await runAxe(page); await page.screenshot({ path: `${OUT}/${cfgName}-offline-spa.png` }).catch(() => {});
    await ctx.setOffline(false);
    await ctx.close();
  }
  void adminEmail; void adminPw;
}

try { await main(); } catch (e) { issues.push({ page: `${cfgName}/${label}`, kind: "fatal", detail: String(e.stack || e).slice(0, 500) }); console.error(e); }
const list = [...findings.values()].map((f) => ({ id: f.id, impact: f.impact, help: f.help, nodes: [...f.nodes].slice(0, 60), pages: [...f.pages].slice(0, 40) }));
const fatal = list.filter((f) => f.impact === "serious" || f.impact === "critical");
const byKind = {}; for (const i of issues) (byKind[i.kind] ||= []).push(i);
const report = { fatal, other: list.filter((f) => !fatal.includes(f)), issues: byKind, notes, ok: fatal.length === 0 && !issues.some((i) => i.kind === "fatal") };
fs.writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 1));
console.log("=== serious/critical axe violations:", fatal.length);
for (const f of fatal) console.log(`- ${f.id} (${f.impact}) ${f.help}\n    pages: ${f.pages.slice(0, 4).join(", ")}\n    nodes: ${f.nodes.slice(0, 4).join(" | ")}`);
console.log("=== other axe:", report.other.map((f) => `${f.id}(${f.impact})`).join(" ") || "none");
console.log("=== issues:", Object.entries(byKind).map(([k, v]) => `${k}=${v.length}`).join(" ") || "none");
await browser.close();
process.exit(report.ok ? 0 : 1);
