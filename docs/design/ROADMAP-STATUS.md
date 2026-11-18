# Roadmap status (updated 2026-11-18)

Phases are from `01-core-spec.md` §11. Status values: **Doing now**, **Can do without input**, **Can do — needs data-safety review first**, **Blocked on decision**. Decision IDs refer to `DECISIONS.md`.

Data-safety review means: an independent agent reviews the code for anything that deletes, overwrites or migrates user data (progress, attempts, streaks) before it ships.

## Phase 0 — Quick wins (`00-review.md` §4)
| # | Item | Status |
|---|---|---|
| 1 | UI language from `navigator.languages` | Doing now (PRs in flight) |
| 2 | Answer-input attributes (autocapitalize etc.) | Doing now (PRs in flight) |
| 3 | Lesson first paint not blocked by review warm-up | Doing now (PRs in flight) |
| 4 | `client_operation_id` on every answer | Doing now (PRs in flight) |
| 5 | Persist/restore in-progress lesson state, "Resume" | Doing now (PRs in flight); local progress storage is data-touching, so see the review note below |
| 6 | Emoji to icons, SVG flags | Doing now (PRs in flight) |
| 7 | Motion tokens and animations | Doing now (PRs in flight) |
| 8 | Docked feedback sheet | Doing now (PRs in flight) |
| 9 | `.page-loading` and skeletons | Doing now (PRs in flight) |
| 10 | Home hero "Continue lesson" | Doing now (PRs in flight) |
| 11 | Logical properties, RTL chevrons, quest aria-label | Doing now (PRs in flight) |
| 12 | `role="progressbar"`, `100dvh` | Doing now (PRs in flight) |
| 13 | Light/Dark/System + theme-color metas | Doing now (PRs in flight) |
| 14 | Keyboard map in the runner | Doing now (PRs in flight) |
| 15 | Onboarding: language then first lesson | Doing now (PRs in flight) |

## Phase 1 — Design system and session engine
| Item | Status |
|---|---|
| `tokens.css`/`tokens.ts`, UI primitives, `/showcase` | Can do without input |
| Extract `SessionEngine` into `packages/shared`, one `<SessionRunner>`, migrate five runners | Can do — needs data-safety review first (runners write attempts and progress) |
| Inline-style migration, skeletons, theme switch, text-size, shortcut sheet | Can do without input |

## Phase 2 — Screens
| Item | Status |
|---|---|
| Today, Path, Practice hub, Library, You/Settings, Completion, four-destination nav | Can do without input, except gamification numbers: Blocked on decision D7 (numbers only; layout proceeds) |
| First-run flow details (goal choices) | Blocked on decision D7 for defaults |
| Accessibility test script | Can do without input |

## Phase 3 — Local store and outbox
| Item | Status |
|---|---|
| `Store` on IndexedDB; local lesson progress; offline storage | Can do — needs data-safety review first (new persistent user data, migrations, eviction) |
| Outbox draining via existing endpoints; sync indicator; remove "session unavailable" wall | Can do — needs data-safety review first (remote-side writes, duplicate/overwrite risk) |
| Workbox precache, update toast | Can do without input |
| Backend `POST /sync/batch` (CONTRACT.md first, Codex lane) | Can do — needs data-safety review first |

## Phase 4 — Local grading, SRS, packs
| Item | Status |
|---|---|
| Golden-vector harness (Python tests as vectors) | Can do without input |
| TypeScript grading port, FSRS and progress rules | Blocked on decision D6 (answers to client) |
| Pack endpoints, pack manager, Downloads settings | Can do — needs data-safety review first (downloaded files, cache eviction) ; offline answers part Blocked on D6 |
| Audio packs | Blocked on decision D8 |
| Server re-grade and parity reporting | Blocked on decision D6 |

## Phase 5 — Shells and stores
| Item | Status |
|---|---|
| Overall shell strategy / freezing `mobile/` | Blocked on decision D1 |
| Windows Store PWA (PWABuilder) | Blocked on decision D3 (domain + TLS); individual account is free (D2 not needed) |
| Android Capacitor shell, internal APK testing | Can do without input after D1 is confirmed; public release Blocked on D2, D3, D9, D10 |
| iOS/iPadOS shell | Blocked on decision D5 (and D12 if social sign-in) |
| Tauri v2 | Blocked on decision D4 (and D6) |

## Phase 6 — Platform delight
| Item | Status |
|---|---|
| Widgets, shortcuts, command bar, window-controls overlay, local notifications | Can do without input (shell-dependent items follow Phase 5) |
| Illustrations, designed sound set | Blocked on decision D11 |
| Streak awards shelf | Blocked on decision D7 |

## Needs data-safety review before any build
Local lesson-progress saving and restore (Phase 0 #5), the IndexedDB `Store`, offline storage and eviction, the outbox/sync endpoint, `SessionEngine` extraction, and pack download/caching. Each gets an independent reviewer given the code (not conclusions), per the standing destructive-code gate.

## Unmerged spec this builds on: `origin/docs/delight-spec`
The core spec's delight/acceptance items (the "D§9.x" references) come from `docs/APP_SPEC_FOR_FABLE_REVIEW.md` §9 on branch `origin/docs/delight-spec` (one commit, `b6773982b`, "add Delight / polish section"; 321 added lines in that single file). It is **not merged**. A trial merge into `fix/wsl-handover-followups` reports a content conflict in `docs/APP_SPEC_FOR_FABLE_REVIEW.md` (the file already exists on the integration branch and differs), so it needs a manual rebase/merge by whoever owns that doc. This PR does not touch it; references to `D§9.x` stay unresolved on this branch until it is merged.
