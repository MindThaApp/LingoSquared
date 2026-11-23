# Owner decisions

All rows were decided by the owner on 2026-11-23. Last updated 2026-11-23.

| ID | Decision | Options | Recommended default | What it blocks | Status |
|---|---|---|---|---|---|
| D1 | One web codebase + thin native shells, and freezing `mobile/` (Expo) | (a) one web codebase, Capacitor/Tauri shells, freeze `mobile/` (b) keep Expo in parallel (c) rewrite natively | One web codebase with Capacitor for Android/iOS and Tauri for Windows; freeze `mobile/`, subject to the native-quality guard below | Phase 5 shells, `android-shell/` replacement, any new work in `mobile/` | Decided by the owner 2026-11-23 |
| D2 | Google Play account type | Personal (closed test: 12 testers x 14 days before production) vs organisation (registered entity + D-U-N-S) | Personal account; complete the 12-testers-for-14-days closed test before production | Play public release, Data safety/listing work timing | Decided by the owner 2026-11-23 |
| D3 | Public domain and TLS | Buy a domain + managed TLS; hosting stays as is | The owner will buy a domain; put managed TLS in front of the server | Microsoft Store PWA, web push at scale, TWA/asset links, social sign-in, any public release | Decided by the owner 2026-11-23 |
| D4 | Does Tauri v2 (offline Windows) keep optional sign-in/sync? | Strictly local profile vs optional sync | Strictly local in v2.0; optional sync later via the outbox | Tauri v2 spec and its data model (v2 only) | Decided by the owner 2026-11-23 |
| D5 | iOS build route | Cloud macOS CI vs local Xcode builds vs PWA only | Build locally with Xcode on the owner's Mac; Apple Developer Program ($99/year); no cloud macOS CI | iPhone/iPad shell, Apple submission, widgets on iOS | Decided by the owner 2026-11-23 |
| D6 | Ship accepted answers to the client for instant offline grading | Yes (server re-grades on sync, stays authoritative) vs No (grading stays online) | Yes; server re-grades on sync and remains authoritative | Phase 4 local grading, full offline-first, Tauri v2 | Decided by the owner 2026-11-23 |
| D7 | Gamification amounts and defaults | XP per exercise/lesson, default daily goal (spec: 3 choices, default 10 min), streak-freeze rules, whether hearts/gems/leaderboard ever turn on | Streaks with freezes, XP, 5/10/15-minute daily goal (default 10), quests and awards; no hearts or new currency; opt-in leaderboards maybe later | Today goal ring, completion screen numbers, quests, awards shelf | Decided by the owner 2026-11-23 |
| D8 | Rendered audio: provider, voices, budget and storage | Cloud TTS vs recorded vs mixed | Render once and store using the language/provider plan below; Opus packs with AAC fallback; expected one-time cost under $15 (verify) | Audio packs, offline audio, Whisper/speech scope | Decided by the owner 2026-11-23 |
| D9 | Native-review status that allows store listing claims | Which courses count as publish-gated | For now, list only courses already publish-gated | Store listings and screenshots | Decided by the owner 2026-11-23 |
| D10 | Privacy contact and public privacy policy / account-deletion web URL | Address/email to publish, hosting page | Publish `mindthaapp@gmail.com`; host the policy and account-deletion page on the D3 domain | Play Data safety, Apple privacy, any store submission | Decided by the owner 2026-11-23 |
| D11 | Illustration (12 line illustrations) and sound-set sourcing | Commission vs in-house vs simple icons only | Make illustrations and the sound set in-house now; export clean files without editor/tool metadata | Empty/error/completion states polish, designed sounds | Decided by the owner 2026-11-23 |
| D12 | Sign-in providers | None / Google / Apple / passkeys / email / Microsoft | Google, Apple, passkeys, email link/code and Microsoft; retain a non-Google option | Sign-in redesign, iOS submission | Decided by the owner 2026-11-23 |

## Decided

- **D1:** Keep one web codebase with Capacitor shells for Android and iOS and Tauri for Windows. Keep the `mobile/` code, but stop its tooling and CI and do no new work there. Use native plugins for audio playback, recording and speech where web APIs fall short. Measure startup time and audio latency on real devices before any store release; revisit this decision if the native quality bar is not met.
- **D2:** Use a Google Play personal account. Complete a closed test with 12 testers for 14 days before production.
- **D3:** The owner will buy a domain. Put managed TLS in front of the server.
- **D4:** Tauri v2 is strictly local in v2.0. Optional sync may be added later via the outbox.
- **D5:** The owner has a Mac and will build iOS locally with Xcode. Join the Apple Developer Program at $99/year. Cloud macOS CI is not needed.
- **D6:** Ship accepted answers to the client. The server re-grades on sync and remains authoritative.
- **D7:** Enable streaks with streak freezes, XP, daily goals of 5, 10 or 15 minutes (default 10), quests and awards. Do not add hearts or a new currency. Leaderboards may be added later, but must be opt-in only.
- **D8:** Render audio once and store it. Keep the existing Google voices for nl, de, en, es, fr, it, hi, ru, pl, ro and ar, using free tiers and spreading rendering over two months. Use Azure neural `fa-IR` voices Dilara and Farid for fa, within the free tier. Use a Gemini Flash TTS Persian (Afghanistan) voice for prs only after a native Dari speaker approves a sample; otherwise use human recordings of core vocabulary. Recorded clips continue to take priority. Fix the approximately 5,500 strings with missing Arabic diacritics before rendering. Do not use MMS-TTS, F5-TTS, XTTS-v2 or Fish Speech because their licences forbid commercial use, and do not use the unofficial Edge read-aloud endpoint. Store per-language packs as mono Opus at about 32 kbps after checking iOS/Safari Opus playback; use AAC as the fallback. Expected one-time cost is under $15 (verify). All prices are marked “(verify)”.
- **D9:** For now, list only courses that are already publish-gated.
- **D10:** Use `mindthaapp@gmail.com` as the public privacy contact for now. Put the privacy policy and account-deletion page on the D3 domain.
- **D11:** Make the illustrations and sound set in-house now; do not commission them. Export clean files with no editor or tool metadata: no SVG generator comments or tool-created `title`/`desc`, and no PNG text chunks.
- **D12:** Support Google, Apple, passkeys, email link/code and Microsoft sign-in. Apple sign-in is required on iOS when other social sign-in exists. Keep a non-Google option for regions where Google is blocked.
