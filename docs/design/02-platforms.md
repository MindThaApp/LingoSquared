# Auvel (LingoSquared) — platform recommendation and adaptations

Date: 2026-11-18. Companion to `01-core-spec.md` (cited as "Core §n") and `00-review.md` (R-n).
Prior decisions respected: Microsoft Store ships as a PWA first via PWABuilder; an offline Tauri app is v2 (`.local/logs/msstore-pwa-readiness.md`, `.local/logs/offline-windows-feasibility.md`). The Play Store account is still an open decision.

Store rules, fees and API availability change. Items marked **(verify)** are from memory and must be checked against the current store documentation before acting on them.

---

## 1. The strategic choice: one web codebase, thin native shells

**Recommendation: keep one React/TypeScript web app and wrap it. Do not build a second UI in React Native or a native toolkit.**

Why, for a solo developer:
- The hard parts of this app are fourteen exercise types, a virtual keyboard, bidi text, transliteration, glossing and a grader with years of content-driven edge cases. They exist once, in web technology, and are verified. A second UI means re-implementing and re-verifying all of them, forever, per content change.
- Web text layout handles RTL, bidi isolation and complex scripts better than any cross-platform native toolkit today.
- The quality gap between this app and a "native-feeling" one is not the rendering engine. It is latency (server grading), lost state, and missing polish (R1–R3). Core §8 removes the first two in shared TypeScript; the design system removes the third. After that a WebView app with native haptics, notifications, widgets and navigation gestures is very hard to tell apart from native for this kind of content.
- The shared core (`packages/shared/src/core`, Core §8.1) is pure TypeScript, so the door to a native UI stays open later if a platform ever justifies it.

Consequences for the repo:
- `frontend/` stays the product.
- `android-shell/` (Capacitor) is the right idea in the wrong state: rebuild it as `shells/android/` with bundled web assets, no `allowMixedContent` (`android-shell/capacitor.config.json:9`), and native plugins.
- `mobile/` (Expo/React Native scaffold, placeholder home at `mobile/app/index.tsx:12-37`) is **frozen**: keep the code, stop its three CI workflows from consuming minutes, do not add screens. Revisit only if store review or performance rejects the WebView approach. This is a proposal for Ramin to decide; nothing is deleted. **⏸ Pending decision (see DECISIONS.md): D1 one codebase / freeze mobile/**

---

## 2. Recommendation matrix

Cost is incremental effort for one developer after the Core phase named in "When". S ≤ 1 week, M 2–4 weeks, L > 1 month. Recurring cost is per year.

| Platform | Verdict | Approach | When (Core §11) | Build cost | Recurring | Benefit |
|---|---|---|---|---|---|---|
| **Web / PWA** | **Yes — primary** | The app itself; installable PWA | Always | — | Domain, TLS, hosting | Every other platform is this plus a shell; zero install friction; instant updates |
| **Windows — Store PWA** | **Yes** | PWABuilder MSIX from the public HTTPS origin | After Phase 2 (design) — sooner if desired | S (plus the domain/TLS/manifest items already listed in the readiness report) | Microsoft developer account; individual registration is now free, company accounts pay a one-time $99 ([Microsoft Windows Developer Blog, Sept 2025](https://blogs.windows.com/windowsdeveloper/2025/09/10/free-developer-registration-for-individual-developers-on-microsoft-store/); [fees](https://learn.microsoft.com/windows/uwp/publish/account-types-locations-and-fees)) — verified 2026-11-18, corrected from earlier note | Store presence, discoverability, auto-update, low risk; desktop is where typing-heavy study happens **⏸ Pending decision (see DECISIONS.md): D3 domain+TLS** |
| **Windows — Tauri (offline)** | **Later (v2)** | Tauri 2 + WebView2 + SQLite + bundled packs/audio/Whisper | After Phase 4 | M (was L: after Phase 4 the grading/SRS port already exists in the shared core) | Same account | True no-server mode, bundled audio, bigger local models; only worth it if "no account, fully offline" is a selling point or hosting is to be avoided **⏸ Pending decision (see DECISIONS.md): D4 sync, D6 answers to client** |
| **Windows — native WinUI 3** | **No** | — | — | L+ and a second UI | — | Nothing the PWA with window-controls overlay cannot approximate; would double all UI work |
| **Android phone** | **Yes** | Capacitor 7+ shell, web assets bundled, native plugins (haptics, local notifications, secure storage, app shortcuts, splash) | Internal track after Phase 3; public after Phase 4 | M | Play account one-time fee; closed-testing requirement for new personal accounts (confirmed: accounts created after 13 Nov 2023 need a closed test with at least 12 testers opted in for 14 continuous days; [Play Console Help](https://support.google.com/googleplay/android-developer/answer/14151465), checked 2026-11-18) | Largest audience for fa/prs learners; best platform for haptics and reminders; Play Store trust **⏸ Pending decision (see DECISIONS.md): D2 Play account type** |
| **Android tablet & foldable** | **Yes — same binary** | Adaptive layouts (Core §6.6) + posture handling | With Android phone | S | — | Free reach; Play ranks apps that meet large-screen quality guidelines higher on those devices **(verify)** |
| **ChromeOS** | **Free** | PWA and the Android build both run | — | — (test keyboard/mouse once) | — | School and budget laptops |
| **iPhone** | **Later** | Interim: PWA (Add to Home Screen; web push works for installed web apps on iOS 16.4+). Then Capacitor iOS shell with SQLite store | After Phase 4 and after Android is stable | M–L (first Apple submission, review iterations, no Mac on hand) | Apple Developer Program, $99/yr ([Apple](https://developer.apple.com/programs/whats-included/)) — verified 2026-11-18; macOS build machine or cloud macOS CI | The audience most sensitive to polish; required for "as good as the best iOS apps" to be literally true **⏸ Pending decision (see DECISIONS.md): D5 iOS build route** |
| **iPad** | **Later — same binary as iPhone** | Universal app, expanded layouts, keyboard/pointer/Pencil support | With iPhone | S on top of iPhone | — | Excellent study device; split view next to a book or video |
| **macOS** | **No (dedicated); free via web** | PWA in Chrome/Edge or Safari "Add to Dock"; optionally allow the iPad app to run on Apple-silicon Macs once the iOS app exists | — | 0–S | — | A dedicated Mac app would need notarisation, a Mac, and yields little over the PWA |
| **Linux desktop** | **No (dedicated); free via web** | PWA | — | 0 | — | Tauri could emit a Linux build later at low cost if anyone asks |
| **Home-screen widgets (Android)** | **Later** | Jetpack Glance widget in the Capacitor project reading a small shared JSON written by the app | Phase 6 | S–M | — | Streak and "due today" at a glance; strongest retention surface that is not a notification |
| **Widgets / Live Activities (iOS)** | **Later** | WidgetKit extension (Swift), shared via App Group | Phase 6, after iPhone | M | — | Same; lock-screen widget for streak |
| **Windows widgets / taskbar** | **Maybe later** | PWA `shortcuts` (jump list) now; app badge for due count; Windows 11 Widgets Board via PWA widgets is possible but niche **(verify support)** | Shortcuts and badge in Phase 5 | S | — | Jump list and badge are cheap and feel native |
| **Apple Watch / Wear OS** | **No** | — | — | L | — | Language exercises need a screen and a keyboard; a watch can at most show a streak complication. Revisit only if a "flashcard glance" mode proves popular on phones |
| **Smart speakers, TV, car** | **No** | — | — | — | — | Out of scope for a solo product |
| **Browser extension / share target** | **No for now** | — | — | — | — | "Save this word" is attractive but is a content-pipeline feature, not a platform |

Order of work: Web/PWA quality → Windows Store PWA → Android (phone + large screens) → iPhone/iPad → widgets → Tauri v2 if still wanted.

### Why Android before iPhone, although iOS sets the quality bar
- No Mac is required; the existing toolchain already builds an APK (`.github/workflows/android-apk.yml`).
- Play review is lighter and iteration is faster.
- The fa/prs and X→en audiences are predominantly on Android.
- iOS WebView storage can be evicted by the system, so iOS must wait for the SQLite-backed store (Core §8.2) to be trustworthy; shipping before that risks the one thing the spec forbids: losing progress.
- The design target remains iOS-level polish on every platform; iOS is deferred as a store target, not as a standard.

### Why not a TWA for Android
A Trusted Web Activity (what PWABuilder emits for Play) is cheaper than Capacitor, but it is a browser tab without native plugins: no rich haptics, no local (offline) notification scheduling, no widget, no bundled starter content for an offline first run, and it requires the public origin plus Digital Asset Links. Capacitor costs a few more days and removes all of those limits. If the Play decision is "try it cheaply first", a TWA is an acceptable two-day experiment after the Windows PWA is live, and can be replaced by the Capacitor build under the same application id later.

---

## 3. One spec or several?

**One master spec (`01-core-spec.md`) plus the adaptation sections below is enough. No platform gets a separate full spec now.**

Reasons:
- Every recommended platform runs the same UI code and the same core; they differ in shell, navigation chrome, input and system integration — exactly what an adaptation section covers.
- A separate full spec is warranted only when a platform has a different product (different feature set, data model or UI toolkit). The single candidate is the **Tauri offline edition**, which drops accounts, sync, leaderboard and server push. Its architecture study already exists (`offline-windows-feasibility.md`), and after Core Phase 4 it is the same app with the sync layer switched off and a local profile. When v2 actually starts, write a short `03-windows-offline-spec.md` (local profile, export/import in place of sync, MSIX packaging, bundled model/audio budgets). It is not written now because its inputs (Phase 4 design, audio sizes, Tauri MSIX tooling at that time) do not exist yet.
- Widgets are small enough to specify inside the platform sections.

---

## 4. Shared adaptation rules (apply everywhere)

- **Layout classes** come from window size, not device type (Core §6.6): Compact < 600, Medium 600–1023, Expanded 1024–1439, Large ≥ 1440; plus the short-height rule (< 520px).
- **Input capability, not platform, drives affordances**: `(hover: hover) and (pointer: fine)` enables hover states and shortcut hints; a hardware keyboard enables the shortcut map on any device (tablets and foldables included); touch always keeps 44px+ targets even on desktop touch screens.
- **Identity is constant, chrome is native.** Colour, type scale, components, motion and sound are the same everywhere. Navigation containers, back behaviour, system bars, text-size source, haptics and notifications follow the platform. The app does not imitate Material or Fluent components wholesale; it adopts their *behaviours*.
- **`platform/*` interfaces** (Core §8.1) are the only place platform code lives: `haptics`, `notifications`, `secureStore`, `files`, `speech`, `appBadge`, `shortcuts`, `share`, `systemBars`, `textScale`.
- **Offline promise is the same everywhere after Phase 4**: lessons, review and practice from downloaded packs; sync when online. Differences are only in what is pre-bundled and how background sync is triggered.

---

## 5. Web / PWA

| Topic | Adaptation |
|---|---|
| Navigation | Core §6.6 exactly. Browser back/forward map to the app's stack; runner routes ask before leaving only if resume could not be saved (it normally can, so no prompt). Deep links for every screen. |
| Input | Touch, mouse and keyboard all first-class. Shortcut map (D§9.8 + Core §4.4). Hover states only under fine pointers. `enterKeyHint`, `inputMode`, autocorrect-off on answer fields (R7). |
| Layout | All four classes. In a browser tab on Compact, the bottom tab bar respects the dynamic toolbar via `dvh` and `env(safe-area-inset-*)`. |
| Conventions | None imposed; neutral. Installed (standalone) mode hides nothing the user needs: every screen has its own back affordance because there is no browser chrome. |
| Notifications | Web Push (existing VAPID flow) for all three reminder kinds, scheduled server-side. Permission asked after the first lesson (existing placement). App Badging API for the due count where supported. |
| Widgets | None. Manifest `shortcuts`: Continue lesson, Review, Practice (localised). |
| Store / distribution | Needs a public HTTPS origin (the standing blocker). Manifest: localised `name`/`short_name`/`description`/`shortcuts`, `dir` and `lang` per locale where the browser supports it, split `any`/`maskable` icons, light and dark `theme_color` via meta tags, `screenshots` wide and narrow, `background_color` matching the default theme (R14). Custom install prompt offered after the second completed lesson, never on first load. |
| Offline | Precache the shell (Workbox); packs in IndexedDB; audio in Cache Storage; `navigator.storage.persist()` after first lesson; Background Sync where available. Safari may evict storage for sites not used for some time unless installed **(verify current policy)** — Settings → Downloads says so on Safari and recommends installing. |

---

## 6. Windows

### 6.1 Store PWA (v1)

| Topic | Adaptation |
|---|---|
| Navigation | Expanded/Large: sidebar on the inline-start edge (NavigationView-like: icon + label rows, collapsible to a rail), You at the bottom. Medium (snapped window): rail. Compact (narrow snapped window): bottom tabs. Back: `Alt+Left`, mouse back button and a back arrow in the title area on pushed screens. |
| Title bar | `display_override: ["window-controls-overlay", "standalone"]`. The title-bar area holds the course chip, a search/command field (`Ctrl+K`) and the sync indicator, laid out with `env(titlebar-area-*)` and marked draggable (`app-region: drag`) except for controls. Falls back to the standard title bar cleanly. |
| Input | Keyboard is the primary input. Full shortcut map; `Ctrl+K` command bar; `Ctrl+,` settings; `Ctrl+1…4` destinations; `F6` cycles panes; `Esc` closes sheets and asks to leave a session; Tab order follows visual order. Mouse: hover states, wheel scrolling, right-click context menu on words (Gloss, Play audio, Add to review, Copy). Touch and pen on Surface: targets stay 44px; pen behaves as a pointer; handwriting works through the Windows handwriting panel in any text field, so no custom ink is needed. Windows IME for fa/prs/other scripts must work in every answer field — composition events never trigger shortcuts. |
| Layout | Default window 1100×760, minimum 360×520. Two-pane Path and Library from Expanded. The exercise column stays at `--content-max` and is centred; the side pane shows lesson outline/notes in Large. Snap layouts (half, third) land in Medium/Compact and must be checked. |
| Conventions (Fluent) | Segoe UI Variable through `system-ui`. Follow the Windows accent? No — keep the brand accent; but honour Windows light/dark, High Contrast (`forced-colors`) and "Show animations" (maps to reduced motion). Mica cannot be used by a PWA (no access to the backdrop); approximate with the app background tinted toward the theme, and do not fake blur. Corner radius of in-app surfaces already matches Windows 11 (8–14px). Context menus, tooltips (500ms delay, keyboard-focus visible) and scrollbars use system behaviour. Language marks instead of flag emoji, which Windows does not render (R9). |
| Notifications | Web Push through Edge delivers native toasts into the notification centre; clicking deep-links via `launch_handler: focus-existing`. Quiet hours follow Windows Focus automatically. Badge on the taskbar icon with the due count (Badging API). |
| Widgets | Jump list from manifest `shortcuts`. Windows 11 Widgets Board: skip in v1. |
| Store requirements | As listed in `msstore-pwa-readiness.md`: public HTTPS origin, stable manifest `id`, icons, at least one desktop screenshot, privacy policy URL with a real contact, IARC questionnaire, a test account for certification, listing text that claims only the publish-gated courses. Add: age statement (13+), disclosure of third-party endpoints (speech model CDN, Sentry). |
| Offline | Same as web. Before Phase 4 the listing must not say "works offline"; after Phase 4 it can. Speech model download is opt-in with its size shown. Persian/Dari audio must come from audio packs — Windows has no usable offline fa/prs voice (feasibility report §4, marked unverified there). |

### 6.2 Tauri offline edition (v2, later)
Same UI. Differences: local profile instead of accounts (optional sign-in to sync could be kept — decide in the v2 spec), SQLite store, packs and audio bundled or side-loaded, Whisper bundled, native window with real Mica available through Tauri window effects, Windows toast notifications scheduled locally, MSIX packaging for the Store. Gets its own short spec when started (§3). **⏸ Pending decision (see DECISIONS.md): D4 optional sync**

---

## 7. Android phone

| Topic | Adaptation |
|---|---|
| Shell | Capacitor, web assets bundled in the APK/AAB (not loaded from a URL), API over HTTPS only, no mixed content. Plugins: Haptics, Local Notifications, Push (FCM, optional), Preferences/secure storage for tokens, App, Splash Screen, Status Bar, Network, Filesystem, Share, and a small custom plugin for the widget data file and app shortcuts. WebView minimum version enforced (show an "update Android System WebView" screen below it). |
| Navigation | Bottom navigation bar with four destinations (label always visible). **System back and predictive back**: back pops the in-app stack; at a root tab it goes to Today; at Today it leaves the app. In a session, back opens "Leave lesson? Your place is saved." The predictive-back gesture must show the previous screen preview — opt in via the manifest and route the Capacitor back event through the app's router. Edge-to-edge: content draws behind system bars with insets applied (`env(safe-area-inset-*)` plus the status-bar plugin); gesture-nav bar area is never used for controls. |
| Input | Touch first. Minimum target 48dp (set `--hit-min: 48px` in the Android shell). Haptics per Core §3.5. Soft keyboard: `windowSoftInputMode=adjustResize` and the visual-viewport API keep the docked Check button above the keyboard; IME action shows "Done" and triggers Check. System keyboards for fa/prs are preferred when installed — the in-app virtual keyboard is offered, not forced, on Android. Hardware keyboards (and DeX) get the full shortcut map. |
| Layout | Compact portrait is the reference (360×640 minimum). Landscape phone uses the short-height rule: collapsed header, prompt beside answer area when width ≥ 600. Font scale from the OS initialises the text-size multiplier; must hold at 200% (Android allows up to 200% non-linear scaling). |
| Conventions (Material You) | Adopt behaviours, not the look: bottom bar, predictive back, edge-to-edge, per-app language (the app registers its locales so the system "App languages" setting works and syncs with the in-app language), themed (monochrome) adaptive icon, splash screen API, system share sheet for export, photo picker not needed. Dynamic colour (wallpaper-based) is **not** used for the accent — the brand and the verdict colours must stay stable and AA-verified; it may tint the widget background only. Ripple-like pressed states come from the app's own press animation. |
| Notifications | Local scheduling via AlarmManager-backed Local Notifications (works offline): daily reminder, streak reminder, review due. Android 13+ runtime permission asked after the first lesson with the in-app pre-prompt. Channels: "Daily reminder", "Streak", "Reviews" so the user can silence one without the others. Exact alarms are not required (inexact is fine, avoids the special permission). Notification actions: "Start" (deep link), "Later" (snooze 1h). |
| Widgets | Phase 6: (1) 2×2 "Streak + goal ring"; (2) 4×2 "Today": next lesson title, due count, Start button; (3) optional 4×1 "Word of the day" from learned words with tap-to-hear. Built with Glance; data comes from a JSON file the web app writes after each session; updated on write and at midnight. Widgets are direction-aware and localised. App shortcuts (long-press icon): Continue lesson, Review, Practice. |
| Store requirements | Decide the Play account (personal accounts created recently must run a closed test before production (confirmed: 12 testers, 14 days, accounts created after 13 Nov 2023; [Play Console Help](https://support.google.com/googleplay/android-developer/answer/14151465), checked 2026-11-18); an organisation account avoids this but needs a registered entity and D-U-N-S). Then: target the current API level; Data safety form (account data, app activity, audio processed but not stored, crash data optional); privacy policy URL; account deletion available in-app and via a web URL (exists in-app: `ProfilePage.tsx`; the web URL is a Play requirement); content rating; declare any foreground service (none needed); 16 KB page-size compatibility for any native libs (confirmed and date corrected: apps targeting Android 15 / API 35 or higher must support 16 KB pages on 64-bit devices; from 1 Feb 2027 updates that do not will be blocked; [Android Developers](https://developer.android.com/guide/practices/page-sizes), checked 2026-11-18); listing claims limited to publish-gated courses; screenshots for phone, 7" and 10" tablets. No payments, so no billing policy exposure. **⏸ Pending decision (see DECISIONS.md): D2 Play account type** |
| Offline | A1 starter packs for the launch courses bundled in the app so first run works with no network. Store: IndexedDB in the WebView for the first release is acceptable on Android (storage is app-private and not evicted while the app is installed); move to SQLite with iOS. Sync on app resume and connectivity change (Network plugin); optional WorkManager job later. Downloads default to unmetered networks, with a per-download override. |

---

## 8. Android tablet and foldable

Same binary and store listing as phone. Additions:

| Topic | Adaptation |
|---|---|
| Navigation | Medium: navigation rail. Expanded: persistent sidebar. No bottom bar above 600dp width. |
| Layout | Two-pane list/detail on Path (unit list + unit detail) and Library (word list + word detail) from 840dp. Today uses two columns. The session runner stays single-column at `--content-max`, centred, with the virtual keyboard limited to the same width (never a full-width 1200px keyboard). In landscape Expanded, teaching notes can sit in a side pane next to the exercise. |
| Foldables | Use the Viewport Segments / device-posture media features where the WebView provides them **(verify WebView support; otherwise read fold bounds through a tiny native plugin)**. Book posture (vertical hinge): never place content across the hinge — panes align to the two segments. Tabletop posture (horizontal hinge, half-open): prompt and audio on the top half, answer area and keyboard on the bottom half. Unfolding mid-session keeps state and position (the engine state is independent of layout). |
| Multi-window | Fully resizable; supports split screen and free-form windows down to Compact; state survives configuration changes (no reload — handle resize in the web layer, declare `configChanges` so the Activity is not recreated). Drag-and-drop of text into answer fields is disabled in sessions (it would paste answers). |
| Input | Keyboard and trackpad/mouse: full shortcut map, hover states, right-click menu, focus rings. Stylus: pointer only in v1; the system handwriting-to-text in text fields (Android 14+ stylus handwriting) works for Latin answers without app code **(verify per script)**. |
| Store | Meet Play's large-screen quality checklist (resizability, keyboard/mouse, no letterboxing, no orientation lock); provide tablet screenshots. ChromeOS gets the same build. |

---

## 9. iPhone

Interim (now): the PWA. On iOS it installs from Safari's Share → Add to Home Screen; web push works for installed web apps; there is no vibration API and storage can be evicted, so the interim is "good, not promised".

Store app (later):

| Topic | Adaptation |
|---|---|
| Shell | Capacitor iOS (WKWebView), bundled assets, SQLite store (required here), Keychain for tokens, plugins as on Android plus a Swift widget extension later. Builds need macOS: use a cloud macOS runner in CI, or a borrowed/rented Mac for the first submissions. |
| Navigation (HIG) | Tab bar with four tabs, labels always shown. Pushed screens have a back button with the previous title at the leading edge and support the **edge-swipe back gesture** (in RTL from the trailing/right edge — WKWebView's built-in swipe navigation is off for SPAs, so implement the interactive gesture in the app with the View Transition or a transform-driven stack). Sheets for modal tasks with a grabber and swipe-down to dismiss; the session runner is a full-screen cover with a close button at the leading top. Large titles that collapse on scroll for Today, Path, Library, You. Scroll-to-top on status-bar tap. No hamburger menus. |
| Input | Touch; haptics through the Taptic engine per Core §3.5 (this is where they matter most). Keyboard: `keyboard-avoidance` via visual viewport; an input accessory row above the keyboard holds the special-character chips and Check. System keyboards for fa/prs preferred; in-app keyboard offered. Dictation key stays available. Respect the silent switch for cue sounds; lesson audio plays with the playback audio session so it is audible in silent mode only after an explicit tap on an audio button. |
| Layout | Compact only. Safe areas for Dynamic Island and home indicator (insets already handled in CSS). Supports the smallest current screen (375×667) and Display Zoom. Text size initialised from Dynamic Type, including accessibility sizes; layouts hold to 200%+. |
| Conventions | SF via `system-ui`; SF-like weights; bounce scrolling left on; pull-to-refresh only on Today (triggers sync); context menus on long-press for words and lessons; system share sheet; Sign in with Apple offered wherever Google sign-in is (store rule; `SocialSignInButtons.tsx` already has Apple). No custom alert styling — destructive confirmations use an action-sheet-styled `Sheet`. |
| Notifications | Local notifications scheduled on device (UNUserNotificationCenter) for the three kinds; permission asked after the first lesson with the pre-prompt; provisional (quiet) delivery is an option to consider. Time Sensitive is not used. Badge shows the due count. |
| Widgets | Phase 6: small "Streak + ring", medium "Today", lock-screen circular (streak) and rectangular (due count). Live Activity: not for v1 (a lesson is too short). App Intents for "Start today's lesson" and "Review" so they appear in Spotlight and Shortcuts. |
| Store requirements | Apple Developer Program; App Privacy "nutrition labels"; privacy policy URL; in-app account deletion (exists); Sign in with Apple parity; microphone and speech usage strings; no remote code beyond WebView content rules; the app must be more than a repackaged website (guideline 4.2) — offline lessons, haptics, notifications and widgets are the answer; export compliance (standard encryption only); age rating. Persian-language listing is allowed; availability by territory is a business/legal check for Ramin **(verify sanctions-related restrictions for the storefronts concerned)**. |
| Offline | Starter packs bundled. SQLite in the app container (included in device backups; exclude audio packs from iCloud backup). Sync on foreground and via BGAppRefreshTask opportunistically. On-device speech recognition used where the language supports it; otherwise Whisper download with consent. |

---

## 10. iPad

Same binary as iPhone (universal). Additions:

| Topic | Adaptation |
|---|---|
| Navigation | Sidebar in landscape/regular width (collapsible to the tab bar in compact width, e.g. Slide Over and narrow Split View). The sidebar lists the four destinations, the learner's courses, and You. |
| Layout | Regular width: two-pane Path and Library; Today in two columns; the runner centred at `--content-max` with optional notes pane in landscape. Must work in every Split View and Stage Manager size, including Compact, and rotate freely. No full-width text lines: reading width stays capped. |
| Input | Hardware keyboard: full shortcut map, and shortcuts are discoverable by holding ⌘ (expose them through the native menu/`UIKeyCommand` bridge so the system overlay lists them). Trackpad/mouse: hover effects, right-click context menus, pointer lift on buttons is not emulated — simple hover highlight only. Apple Pencil: pointer in v1; **Scribble** works in standard text fields, which gives handwriting input for supported languages without app code; a dedicated handwriting exercise (tracing Persian letters) is a strong future feature for script learners and would be the first thing that justifies native code. |
| Conventions | Popovers instead of bottom sheets for small pickers in regular width; context menus; drag and drop disabled in sessions; multiple windows not supported in v1 (single scene). |
| Notifications / widgets | As iPhone, plus large widget "This week" (week strip + ring + next lesson). |
| Store | iPad screenshots (12.9"/13"); must not be an upscaled phone UI. |
| Offline | As iPhone. |

---

## 11. macOS (no dedicated app)

- Supported path: install the PWA from Chrome/Edge, or Safari → File → Add to Dock. It gets the Expanded/Large layouts, the full shortcut map with ⌘ in place of Ctrl, and web push.
- Small adaptations in the web app: show ⌘ glyphs when the platform is macOS; leave room for the traffic-light controls when window-controls overlay is active; respect "Reduce motion" and "Increase contrast".
- After the iPad app exists, enabling "Designed for iPad" on Apple-silicon Macs is a checkbox-level decision; do it only if it tests well with keyboard and pointer.
- A Tauri macOS build is technically cheap once the Windows Tauri edition exists but needs a Mac and notarisation; not planned.

---

## 12. Cross-platform checklist per release

For each platform that ships, before release:
1. One full lesson, one review session and one practice set in en→nl, en→prs and prs→en.
2. Airplane-mode pass (after Phase 4) including app restart.
3. Keyboard-only pass where a hardware keyboard can exist; screen-reader pass (NVDA / TalkBack / VoiceOver).
4. Largest text size and smallest supported window.
5. Light, dark and high contrast.
6. Notification tap lands in the right session; badge/widget numbers match the app.
7. Upgrade from the previous version keeps all local progress (never ship a build without this test — a migration that loses a streak is the worst bug this app can have).
8. Store listing claims match the publish-gated content.

## 13. Decisions needed from Ramin

1. Confirm "one web codebase + shells" and freezing `mobile/` (Expo).
2. Play account: personal (closed-test requirement) or organisation. Until decided, Android work can proceed to internal APK testing.
3. Domain and TLS — still the gate for the Store PWA, web push at scale, TWA/asset links and social sign-in.
4. Whether the Tauri v2 edition keeps optional sign-in/sync or is strictly local.
5. iOS timing and how builds will be made without a Mac (cloud macOS CI vs hardware).
6. Whether shipping accepted answers to the client is acceptable (required for instant, offline grading; Core §8.3).
