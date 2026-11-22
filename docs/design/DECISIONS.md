# Decisions parked for the owner

Status of every row: **Pending the owner**. Work that does not depend on a row proceeds; work that does is marked "⏸ Pending decision (see DECISIONS.md)" in `01-core-spec.md` and `02-platforms.md`. Last updated 2026-11-18.

| ID | Decision | Options | Recommended default | What it blocks | Status |
|---|---|---|---|---|---|
| D1 | One web codebase + thin native shells, and freezing `mobile/` (Expo) | (a) one web codebase, Capacitor/Tauri shells, freeze `mobile/` (b) keep Expo in parallel (c) rewrite natively | (a): keep `mobile/` code, stop its tooling and CI, no new work | Phase 5 shells, `android-shell/` replacement, any new work in `mobile/` | Pending the owner |
| D2 | Google Play account type | Personal (closed test: 12 testers x 14 days before production) vs organisation (registered entity + D-U-N-S) | Personal for now; internal-track APK testing proceeds meanwhile | Play public release, Data safety/listing work timing | Pending the owner |
| D3 | Public domain and TLS | Buy a domain + managed TLS; hosting stays as is | Register a domain, put TLS in front of the server | Microsoft Store PWA, web push at scale, TWA/asset links, social sign-in, any public release | Pending the owner |
| D4 | Does Tauri v2 (offline Windows) keep optional sign-in/sync? | Strictly local profile vs optional sync | Strictly local in v2.0; add sync later via the outbox | Tauri v2 spec and its data model (v2 only) | Pending the owner |
| D5 | iOS build route without a Mac | Cloud macOS CI (GitHub Actions / Codemagic) vs buy/borrow a Mac vs PWA only | PWA now; cloud macOS CI when iOS starts | iPhone/iPad shell, Apple submission, widgets on iOS | Pending the owner |
| D6 | Ship accepted answers to the client for instant offline grading | Yes (server re-grades on sync, stays authoritative) vs No (grading stays online) | Yes, per Core §8.3 (little to gain by cheating in a single-learner app) | Phase 4 local grading, full offline-first, Tauri v2 | Pending the owner |
| D7 | Gamification amounts and defaults | XP per exercise/lesson, default daily goal (spec: 3 choices, default 10 min), streak-freeze rules, whether hearts/gems/leaderboard ever turn on | Keep hearts/gems/leaderboard off; goal choices 5/10/15 min; no new currency | Today goal ring, completion screen numbers, quests, awards shelf | Pending the owner |
| D8 | Rendered audio for nl/fa/prs: provider, voices, budget | Cloud TTS vs recorded vs mixed | Cloud TTS first, native review of a sample | Audio packs, offline audio, Whisper/speech scope | Pending the owner |
| D9 | Native-review status that allows store listing claims | Which courses count as publish-gated | List only courses already publish-gated | Store listings and screenshots | Pending the owner |
| D10 | Privacy contact and public privacy policy / account-deletion web URL | Address/email to publish, hosting page | Dedicated project email (not personal), page on the domain from D3 | Play Data safety, Apple privacy, any store submission | Pending the owner |
| D11 | Illustration (12 line illustrations) and sound-set sourcing | Commission vs generate vs simple icons only | Icons and simple SVG first; commission later | Empty/error/completion states polish, designed sounds | Pending the owner |
| D12 | Social sign-in providers | None / Google / Apple (Apple required on iOS if any social login) | Defer until D3; Google only if added | Sign-in redesign, iOS submission | Pending the owner |
