# Source map: remaining languages (es, fr, it, ru, zh, ro, pl, hi,
# Arabic dialects, and nl/fa/prs supplements)

Research pass extending the sourcing work already done for Arabic MSA
(`SOURCES_ARABIC_MSA.md`) to every other language this project has
scoped or might scope. Follows the standing policy in `CLAUDE.md`
("Sourcing policy widened...") and `docs/content/AUTHORING_GUIDE.md`
§10: public-domain FSI/DLI/Peace Corps material is immediately usable
(never verbatim — modernize per §10); CC-BY needs a not-yet-built
attribution surface (map it, mark BLOCKED-CC-BY, don't use yet); CC
BY-SA and the categorical exclusions (DLI GLOSS/Headstart2,
OpenSubtitles corpora, Anki decks, commercial apps/textbooks) are
excluded outright.

**Method note**: Exa (`web_search_exa`/`web_fetch_exa`) was used to
find candidates, seeded with the known-good yojik.eu FSI/DLI pages and
the COERLL precedent to surface siblings. Extraction quality was
spot-checked directly — one representative PDF per source downloaded
via `curl` and run through `pdftotext -layout`/`pdfinfo`, not assumed
from search-result highlights alone (Exa's own indexed highlights can
come from a *site's* OCR of a PDF that differs from what a fresh
`pdftotext` pass on the raw file actually yields — verified against
the real file each time, same discipline as the Arabic MSA pass). Not
every candidate's audio was inventoried in depth — text/extraction
quality was the priority per the task's depth-over-breadth framing.

---

## Spanish (es) — lane parked per CLAUDE.md, mapped for when it resumes

Already investigated and decided in `AUTHORING_GUIDE.md` §10
(2026-07-07): **FSI Spanish Basic Course** (PD, 4 volumes, 55 units,
drills + audio, on Live Lingua/fsi-language-courses.org) is the
primary candidate, ready to scaffold once es resumes. COERLL's
Trayectos/Hecho en Texas (also Spanish OER, e.g. the newer "Estamos
aquí!" found this pass, CC-BY-NC-SA) are **CC BY-SA-family and
categorically excluded** — not re-litigated here, §10 already closed
this. Peace Corps Spanish also exists per §10's note but wasn't
re-verified this pass (parked lane, low priority to re-check until es
resumes). **No new work needed here — defer to §10 until es resumes.**

---

## French (fr) — lane parked per CLAUDE.md, mapped for when it resumes

Already investigated and decided in `AUTHORING_GUIDE.md` §10: **FSI
French Basic Course** (PD, 2 volumes ~476+577pp, with audio) is
primary. **COERLL's Français interactif (CC BY 3.0, commercial use
allowed)** is usable *only* once a real attribution-credit surface is
built (hard precondition, not yet done). Not re-verified this pass —
parked lane, §10 is authoritative and current.

---

## Italian (it)

### 1. FSI Italian FAST (Familiarization and Short-Term Training) — primary candidate

- **URL**: `https://fsi-languages.yojik.eu/languages/oldfsi/languages/Italian/FAST/FSI - Italian Familiarization and Short term Training - Volume 1.pdf`
  (Volume 2 sibling at the same path); per-lesson MP3s and an "Updated"
  re-recorded audio set also hosted alongside at
  `fsi-languages.yojik.eu/languages/FSI/Italian/FAST/`.
- **Covers**: 30 lessons across 2 volumes (Vol 1: lessons I–XX +
  regional-Italy info; Vol 2 continues through XXX + recipes from
  lesson XXI on). Communicative/situational (not grammar-sequenced) —
  social, logistical, and workplace situations, explicitly designed
  for use with an instructor. 1992 revision — noticeably more modern
  register than the 1960s-70s FSI norm elsewhere in this project, but
  still needs the standard §10 modernization pass.
- **License/provenance**: `pdfinfo` confirms `Author: Foreign Service
  Institute`; genuine US federal work, public domain (17 U.S.C. §105),
  same basis as every other FSI course already in use.
- **Extraction quality — verified directly**: `pdftotext -layout`
  yields ~585,000 characters of clean, real OCR text across 456 pages
  (`Producer: Adobe Acrobat 9.1 Paper Capture Plug-in` — a real OCR
  pass, not a raw scan). Readable front matter, table of contents, and
  lesson text extract cleanly — the best extraction quality found in
  this entire research pass, better than the Arabic/Russian/Hindi
  scanned dead-ends below. **Best available Latin-script PD source
  found this pass.**
- **Audio**: Per-lesson MP3s for both the original and an "Updated"
  re-recorded set — real recorded audio, pronunciation-reference use
  per the standing §10 caveat (not spliceable directly).
- **Fitness verdict**: **Best candidate for the first en→it A1 wave.**
  Clean text extraction (no page-image-reading burden, unlike most of
  this pass's other finds), real audio, genuine PD, communicative
  framing that's closer to modern CEFR-style pedagogy than the typical
  1960s FSI grammar-drill format.

### 2. FSI Italian Programmed Course / Headstart — secondary/backfill

- **URL**: `fsi-languages.yojik.eu/languages/oldfsi/languages/italian-programmed-course.html`
  (Student Text + Instructor's Manual) and
  `.../italian-headstart.html` (Modules 1–3, 4–5, Glossary, Cultural
  Notes).
- **Covers**: Programmed Course covers the sound system and basic
  grammatical categories (present tense primarily, some past/future);
  Headstart is a shorter survival-level module set with its own
  glossary and culture notes.
- **License/provenance**: Same FSI/PD basis. Not the Headstart2/GLOSS
  exclusion — this is the plain FSI Headstart product, not the
  DLIFLC-hosted third-party-media one flagged in §10.
- **Extraction quality**: Not sampled directly this pass (not needed —
  candidate #1 already clears the bar); flag as unverified but likely
  similar scan/OCR mix to Italian FAST given the same hosting era.
- **Fitness verdict**: Depth/backfill source once FAST's 30 lessons are
  exhausted, not separately verified.

**Recommendation**: FSI Italian FAST (candidate #1) — real depth, real
audio, and the cleanest text extraction found anywhere in this pass.

---

## Russian (ru)

### 1. Yojik's re-OCR'd "FSI Russian Fast Course" (community-remastered) — primary candidate

- **URL**: `https://fsi-languages.yojik.eu/yazik/Downloads/FSI-book-stressed.pdf`
  (also split per-chapter at `.../FSI-chap{N}-stressed.pdf`), indexed
  from `fsi-languages.yojik.eu/yazik/FSI-Russian/FSI-russian.html`.
- **Covers**: The full FSI Russian FAST course, re-typeset — table of
  contents alone runs to page xviii before Lesson 1 begins; sampled
  chapter 1 (17pp) covers the Russian alphabet + phonetics with
  exercises. A genuinely large multi-lesson course (370 pages in the
  combined PDF).
- **License/provenance**: Original content is the FSI Russian FAST
  Course (US federal work, PD). The maintainer's own page states they
  "OCR'd this course and formatted it using the docbook tools" —
  a derivative *presentation* of PD text, not a new copyrighted work;
  same category as any other re-typeset/re-hosted PD material.
- **Extraction quality — verified directly**: This is the standout
  find of the whole pass for a non-Latin script. `pdftotext -layout`
  on the combined PDF (`Creator: DocBook XSL Stylesheets`, `Producer:
  Apache FOP`) yields ~608,000 characters of **clean, real Cyrillic
  Unicode text, including stress marks** (Ру́сский алфави́т extracts
  correctly, not garbled) — a genuine, modern, text-searchable PDF, not
  an image scan. This is dramatically better than every other
  non-Latin-script source checked this pass (Hindi, both Arabic
  dialects below).
- **Audio**: Original FSI tapes are cross-linked per-lesson from the
  same maintainer's page (pronunciation reference only, standard
  caveat).
- **Fitness verdict**: **Best candidate for en→ru, full stop** — real
  depth, genuinely clean Cyrillic text extraction (no page-image
  reading needed, a first for a non-Latin script in this project's
  research so far), real audio cross-referenced. Still needs the
  standard §10 modernization pass (1960s-70s Soviet-era register/
  cultural framing).

### 2. FSI "Russian: An Active Introduction" (original scan) — secondary, scanned dead-end for direct extraction

- **URL**: `fsi-languages.yojik.eu/languages/FSI/Russian/Active Introduction/FSI - Russian Active Introduction - Student Text.pdf`
- **Covers**: A catalog of combinable sentences for daily-activity
  dialog sequences (comings/goings, appointments, errands) — a
  different pedagogical shape than the Fast Course (frame-based vs.
  lesson-based).
- **License/provenance**: Same FSI/PD basis, `Author: Foreign Service
  Institute` confirmed via `pdfinfo`.
- **Extraction quality — verified directly**: `Producer: Adobe Acrobat
  8.1 Image Conversion Plug-in` — a raw scan, zero embedded text layer
  (`pdftotext` yields ~1 byte/page). Page-image reading only.
- **Fitness verdict**: Secondary/structural-variety source once
  candidate #1's Fast Course is exhausted — not needed for depth given
  how large candidate #1 already is, but a different exercise shape
  (sentence-combination drills) worth knowing about.

**Recommendation**: The yojik.eu re-OCR'd Russian Fast Course
(candidate #1) — arguably the single best-extraction non-Latin-script
source found in this whole research pass, and should be tried FIRST
for any future Cyrillic-script (or generally non-Latin) language
search: check whether a community re-OCR/re-typeset exists before
accepting an original scan as a dead end.

---

## Mandarin Chinese (zh)

### 1. FSI Standard Chinese: A Modular Approach — primary candidate, text extraction is a scanned dead-end

- **URL**: `https://archive.org/details/FSI-StandardChinese-StudentTexts`
  (per-module files, e.g.
  `FSI-StandardChinese-Module01ORN-StudentText.pdf`); full audio+text
  course also at `archive.org/details/FSIStandardChinese` (120+ hours
  of audio cited).
- **Covers**: Modular, situation-based (not linear lessons) — Module 1
  Orientation, Module 2 Biographic Info, Module 3 Money, Module 4
  Directions, Module 5 Transportation, Module 6 Meeting, Module 7
  Social, Module 8 Travel, plus optional modules (Car, Hotel,
  Marketing/Business, Post Office, Restaurant, Welfare). Designed to
  reach Level 3 proficiency; a large, real course by any measure.
- **License/provenance**: `Author: Foreign Service Institute` per
  `pdfinfo`; archive.org's own listing tags it explicitly "Usage:
  Public Domain." Same FSI/PD basis as every other course in this
  project.
- **Extraction quality — verified directly**: Sampled Module 1's
  Student Text (96 pages, `Producer: PDFScanLib v1.2.2 in Adobe
  Acrobat 7.0.5`) — `pdftotext` yields ~1 byte/page, a pure image scan
  with zero text layer. **This is expected and not disqualifying** for
  CJK specifically: even a "successful" OCR pass on 1970s-quality
  scanned Chinese characters would need CJK-aware OCR tooling this
  research pass didn't attempt (plain `pdftotext` cannot recover text
  that was never embedded). Page-by-page image reading is the only
  path, same as the already-accepted Peace Corps Dari/DLI Arabic
  precedent — just guaranteed rather than "sometimes."
- **Audio**: Extensive — this is one of the most audio-complete FSI
  courses found (120+ hours cited on archive.org), useful as a
  pronunciation/tone reference during any future recording pass.
- **Fitness verdict**: Best available candidate — real depth, real
  audio, genuine PD — but budget the heaviest page-image-reading
  authoring cost of any language in this pass (worse even than Arabic,
  since there's no partial-OCR English front matter to lean on the way
  FSI Written Arabic Vol 1 had).

**Recommendation**: FSI Standard Chinese (candidate #1) is the only
real option surfaced this pass — no COERLL-style modern CC-BY Chinese
course was found with a Gateway to Chinese level of depth (COERLL's
"Gateway to Chinese" project was mentioned only as a project title in
search results, not independently verified this pass — flag as a
possible future CC-BY lead once attribution infra exists, not
evaluated further here). Treat zh as the **highest per-unit authoring
cost** of any language mapped in this document.

---

## Romanian (ro)

### 1. Peace Corps Romania "Survival Romanian" pre-departure lessons — primary candidate, thin

- **URL**: `https://fsi-languages.yojik.eu/languages/PeaceCorps/Romanian/RO_Romanian_Language_Lessons.pdf`
  (mirrored at `files.peacecorps.gov`)
- **Covers**: 10 short lessons — alphabet, greetings, self-introduction,
  days of week, numbers (small + large), shopping/colors, restaurant,
  orientation/directions, everyday phrases. Genuinely A0/A1 survival
  level, explicitly "everything you need to get by the first days."
- **License/provenance**: US Peace Corps, PD, same basis as prs.
- **Extraction quality — verified directly**: A real native PDF (not
  scanned) — `Producer: Acrobat Distiller 7.0`, `pdftotext` extracts
  ~31,000 clean characters across 14 pages including Romanian
  diacritics (ă/â/î/ș/ț) and IPA-ish transliteration guides intact.
  Genuinely the easiest-to-extract source in this entire pass alongside
  Italian.
- **Fitness verdict**: Clean and immediately usable, but **shallow** —
  10 lessons is barely enough to scaffold a first A1 unit or two, not
  a full A1 course. Good starting vocabulary/phrase scaffold, not a
  standalone source for real depth.

### 2. Peace Corps Romania "Limba Română" Pre-Service Training Manual (ED401768) — deeper but scanned dead-end

- **URL**: `fsi-languages.yojik.eu/languages/PeaceCorps/Romanian/ED401768.pdf`
  (also on ERIC as ED401768, 1995)
- **Covers**: The actual multi-week pre-service training manual (124
  pages) — real depth beyond the survival guide, the kind of course
  structure that could scaffold real A1/A2 content.
- **License/provenance**: US Peace Corps, PD.
- **Extraction quality — verified directly**: `Producer: Acrobat
  PDFWriter 3.02 for Windows NT`, `pdftotext` yields ~192 bytes across
  124 pages — a scanned dead-end, zero text layer. Page-image reading
  required for the real depth.
- **Fitness verdict**: The actual depth source, but budget page-image
  reading time — same shape as the Peace Corps Dari/Moroccan-Arabic
  precedent (a short clean-text companion piece exists, but the real
  course body is scanned).

### 3. Other Peace Corps Romania materials, not sampled — noted for completeness

The same Yojik Romanian index (`languages/PeaceCorps/Romanian.html`)
also lists a Grammar Handbook, a reading/writing practicum, "Limba
Noastra-i o Comoara," and "First Steps in Romanian" — none downloaded/
sampled this pass; worth a follow-up pass if ro is ever prioritized
beyond a first unit or two.

**Recommendation**: Use candidate #1 (clean, 10 lessons) to scaffold
the very first A0/A1 vocabulary, then move to candidate #2's
page-image reading for real depth — same "thin clean-text + deep
scanned" pattern seen in Egyptian/Levantine Arabic and Hindi below.
Note ro is **not currently one of the project's 18 scoped launch
paths** per root `CLAUDE.md` — this mapping is exploratory, for if/when
it's added.

---

## Polish (pl)

### 1. FSI "Communicating in Polish" (pictorial course) — primary candidate, clean text

- **URL**: `https://files.eric.ed.gov/fulltext/ED096842.pdf` (also
  likely mirrored on yojik.eu under FSI Polish, not directly located
  this pass)
- **Covers**: A pictorial, photograph-driven course — narrations and
  dialogs based on real photographs of daily life in Poland (1974,
  Bernard Penny & Krystyna Malinowska), with two sets of comprehension
  questions per selection. Designed to work at multiple levels
  (vocabulary-building for beginners, full communicative use for
  advanced students) rather than one fixed level.
- **License/provenance**: `pdfinfo` confirms real FSI/State Dept.
  authorship per the extracted preface ("FOREIGN SERVICE INSTITUTE
  BASIC COURSE SERIES... For sale by the Superintendent of Documents,
  US Government Printing..."), same PD basis.
- **Extraction quality — verified directly**: `pdftotext -layout`
  yields ~658,000 clean characters across 273 pages
  (`Producer: CVISION Technologies` — a real OCR pass), including
  Polish diacritics (ą/ć/ę/ł/ń/ó/ś/ź/ż) intact in the sampled preface
  text. Second-best Latin-script extraction quality in this whole
  pass, after Italian.
- **Fitness verdict**: Good primary candidate — real photographic/
  situational content, clean extraction, genuine depth (273pp).

### 2. DLI Polish Basic Course (ERIC ED033357) — secondary, much deeper, OCR quality is workable but noisy

- **URL**: `https://archive.org/stream/ERIC_ED033357/ERIC_ED033357_djvu.txt`
  (full text) / `archive.org/details/ERIC_ED033357` (PDF)
- **Covers**: 15 volumes, 168 lessons (per the document's own abstract)
  — a genuinely massive DLI Basic Course, audio-lingual style
  (dialogs + pattern drills), designed to Level 3 proficiency across
  all four skills. By far the deepest single Polish source found.
- **License/provenance**: Defense Language Institute (DoD), PD federal
  work — same category as the DLI Dari precedent already in use, not
  the excluded GLOSS/Headstart2 category (this is the plain Basic
  Course).
- **Extraction quality — verified directly**: Archive.org's own OCR
  text file (`ERIC_ED033357_djvu.txt`) is ~3.5MB of real, largely
  readable text — legible but noisy (classic 1960s-70s typewriter-scan
  OCR artifacts: "disigned" for "designed," stray line breaks,
  occasional garbled words), not as clean as candidate #1's modern
  CVISION-OCR'd version but genuinely usable with more manual
  cross-checking than a page-image-only source would need. **Notably
  better than the fully-scanned dead-ends found for Russian's Active
  Introduction, both Arabic dialects, and Hindi below** — worth
  spot-checking a source's *actual* archive.org OCR text file directly
  before assuming "scanned = dead-end."
- **Fitness verdict**: The real depth source once candidate #1's 273pp
  are exhausted — noisy but workable OCR, not a page-image-reading
  requirement.

**Recommendation**: Candidate #1 (Communicating in Polish) for the
first wave — clean extraction, real situational content; candidate #2
(DLI Basic Course) for depth beyond that, budgeting extra proofreading
time for OCR noise rather than full page-image reading. Like ro, **pl
is not currently a scoped launch path** — mapped exploratorily.

---

## Hindi (hi)

Already an active but small course per root `CLAUDE.md`'s "Seeded
courses" note (hi has real content authored, `AUTHORING_GUIDE.md`
already documents a Devanagari tokenizer footgun). This section maps
PD source depth specifically, which hadn't been done yet.

### 1. FSI/Peace Corps "Hindi: An Active Introduction" (1970) — scanned dead-end

- **URL**: `fsi-languages.yojik.eu/languages/PeaceCorps/Hindi/Fsi-HindiActiveIntroduction-StudentText.pdf`
  (also `.../FSI/fsi-hindi.html`, and on Wikimedia Commons)
- **Covers**: A joint FSI+Peace Corps introduction to conversational
  Hindi (D.N. Sharma & James W. Stone), 143 pages.
- **License/provenance**: Confirmed dual PD basis — both a "work of a
  United States Department of State employee" (17 U.S.C. §101/§105)
  AND independently a Peace Corps work, per Wikimedia Commons' own
  license tags on the same file.
- **Extraction quality — verified directly**: `Producer: Adobe Acrobat
  7.08 Image Conversion Plug-in`, `pdftotext` yields ~1 byte/page —
  fully scanned, zero text layer, as expected for a Devanagari-script
  1970 course.
- **Fitness verdict**: Real, genuinely PD, correctly-leveled beginner
  content — but page-image reading only.

### 2. "Hindi Basic Course" (Center for Applied Linguistics/FSI, 1960, archive.org) — OCR is actively unusable, worse than a plain scan

- **URL**: `archive.org/details/HindiBasicCourse`
- **Covers**: 367 pages, sentence-based with drills, pronunciation
  word-list + glossary of phonetic terms.
- **License/provenance**: archive.org tags it "Public Domain Mark
  1.0," FSI-adjacent (Center for Applied Linguistics, Washington DC,
  1960) — same PD-eligible category as the rest of this document's
  sources, not independently re-verified beyond the platform's own tag.
- **Extraction quality — verified directly, and this is a genuine
  trap**: archive.org's own OCR (`Ocr_detected_script: Latin`,
  `Ocr_detected_lang: ne` (!), `tesseract 5.3.0`) ran **Latin-alphabet
  OCR against Devanagari-script pages**, producing ~1.2MB of complete
  garbage — a stream of unrelated Devanagari-*looking* characters that
  don't correspond to the actual page content at all (sampled directly:
  compare `है ६ # ०४१ रि ६ 5` against what should be real title-page
  text). **This is actively worse than a plain "zero text layer"
  scan** — a naive pipeline that trusts "this file has an OCR text
  layer" as a proxy for "this file is usable" would silently ingest
  nonsense. Confirms the standing Devanagari-tokenizer footgun's
  underlying cause isn't just the project's own compiler regex — the
  upstream source material's own automated OCR is genuinely unreliable
  for Devanagari, a strictly worse starting point than a clean scan
  with no text layer at all.
- **Fitness verdict**: **Do not use the archive.org OCR text for this
  file under any circumstance** — treat it exactly like a scanned
  dead-end (page-image reading only), and flag this specific failure
  mode (garbage OCR masquerading as real text) for anyone sourcing
  future Devanagari — or likely any non-Latin-script — archive.org
  material: verify the actual extracted text is legible before trusting
  an "OCR available" indicator.

**Recommendation**: Both real PD sources for hi require page-image
reading — no clean-text shortcut exists (unlike the Russian find
above). Candidate #1 (FSI/Peace Corps Active Introduction, 143pp) is
the better-scoped and safer of the two given candidate #2's OCR trap;
use it as the primary scaffold, and treat any future Devanagari
archive.org OCR text with active suspicion rather than default trust.

---

## Arabic dialects: Egyptian and Levantine

(MSA itself is already fully mapped in `SOURCES_ARABIC_MSA.md` —
this section covers the two dialect tracks that document explicitly
flagged as future work, plus one already-excluded caution repeated
here for completeness.)

### Egyptian Arabic

#### 1. DLI Egyptian Arabic Basic Course — primary candidate, scanned dead-end

- **URL**: `fsi-languages.yojik.eu/languages/DLI/Arabic-Egyptian/Books/Mod 01.pdf`
  (12 modules total per the site's own listing — Mod 01 through Mod
  12, plus Homework Keys, Self-Evaluation Keys, and a combined
  Speaking Exercises file)
- **Covers**: Module 1 alone (sampled) = Lessons 1-4 ("Greeting
  People," "Meeting People"), December 1981, DLIFLC. 12 modules
  implies a real, substantial course — likely comparable in scope to
  the DLI Arabic (MSA) Basic Course already mapped.
- **License/provenance**: Defense Language Institute Foreign Language
  Center, DoD federal work — same PD basis as every other DLI course
  in this project, and (per the same reasoning already applied in
  `SOURCES_ARABIC_MSA.md`) distinct from the excluded GLOSS/Headstart2
  category — this is the plain dialect-specific Basic Course.
- **Extraction quality — verified directly**: `pdftotext` on Module 1
  (176 pages) yields ~176 bytes total — a pure scanned dead-end, zero
  text layer, matching the exact pattern already found for the DLI
  Arabic (MSA) Basic Course in the prior research pass.
- **Fitness verdict**: Real depth (12 modules), genuine PD, but 100%
  page-image reading — the same cost profile already documented for
  DLI Arabic MSA. Good candidate for a future Egyptian-dialect track
  once approved, budgeting the same heavy authoring cost as MSA's DLI
  option.

### Levantine Arabic

#### 1. FSI Levantine Arabic Course — primary candidate, thin text component

- **URL**: `fsi-languages.yojik.eu/languages/FSI/Arabic/Levantine Arabic/Fsi-LevantineArabic-Pronunciation-StudentText.pdf`
  (plus a separate FSI comparative document,
  `FSI - Levantine and Egyptian Arabic - Comparative Study.pdf`,
  already found in the MSA pass)
- **Covers**: The course structure is primarily **tape-indexed**, not
  lesson-indexed — the old FSI page maps letter-coded content ranges
  (B.1–F.5, F.6–G.7, etc.) directly to 10 numbered tapes with no
  separate per-lesson student-text PDF found this pass beyond the
  Pronunciation student text. This suggests the real content lives
  predominantly in audio, with the written component comparatively
  thin relative to Egyptian's 12-module DLI course.
- **License/provenance**: FSI, PD, same basis as all FSI content.
- **Extraction quality — verified directly**: The Levantine/Egyptian
  **Comparative Study** PDF (already downloaded during the MSA pass)
  is 59 pages, `pdftotext` yields ~59 bytes — scanned, zero text layer.
  The Pronunciation student text specifically wasn't separately
  downloaded this pass (single-file, likely same scanned-era
  provenance given identical hosting/timestamp pattern as its Arabic
  siblings) — treat as scanned until verified.
- **Fitness verdict**: Weaker candidate than Egyptian for a written-
  course adaptation specifically — the real content is audio-primary
  (10 tapes) rather than a clean lesson-by-lesson text course. Would
  need real audio transcription work (a much heavier lift than
  page-image-reading a written text), not just OCR-adjacent authoring.
  Consider Egyptian first if only one dialect track is approved.

**Recommendation for dialects**: **Egyptian Arabic (DLI, 12 modules)
over Levantine** for a first dialect-track wave — comparable
page-image-reading cost to the already-accepted DLI Arabic MSA
precedent, and a real lesson-by-lesson written structure, versus
Levantine's audio-primary, tape-indexed shape which would need
transcription rather than just page images. Both remain **out of
scope until a dialect track is explicitly approved** per
`SOURCES_ARABIC_MSA.md`'s own framing — this section only extends
that document's "flagged for a future pass" items, it does not
constitute an approval to start authoring either dialect.

---

## Supplement check: fa / prs / nl (already-active languages)

Per the task's instruction to check for "better fa/prs/nl supplements"
— one new, real finding:

### nl: DLI Dutch "Intermediate-Advanced Level Refresher Course" — genuine new supplement

- **URL**: `fsi-languages.yojik.eu/languages/DLI/Dutch/Book 01 Part 01.pdf`
  (8 volumes total, Books I–IV each in two parts, per
  `fsi-languages.yojik.eu/languages/DLI/DLI-Dutch.html`)
- **Covers**: Explicitly **above** the level of the FSI Dutch Basic
  Course nl already uses — "begins on the intermediate level" (per
  ERIC ED025774's abstract), Book I covers the sound system + English-
  Dutch contrastive phonology, Books II-III are 6 units × 7 lessons
  each (dialogs, substitution drills, tests), Book IV is 25 lessons on
  interrogation + military terminology (**note**: Book IV's military/
  interrogation register is almost certainly NOT appropriate to adapt
  even after modernization — flag for skip when this source is
  actually used, don't treat "PD" as "automatically fine to adapt,"
  same spirit as §10's existing register-fitness checks).
- **License/provenance**: DLI (DoD), PD federal work — same basis as
  every other DLI course already in active use for nl/fa/prs.
- **Extraction quality — verified directly**: `pdftotext` on Book 01
  Part 01 (210 pages) yields ~210 bytes — scanned, zero text layer.
  Page-image reading required, unlike the clean FSI Dutch Basic Course
  text nl currently draws from.
- **Fitness verdict**: **Real, previously-unmapped supplement for nl's
  eventual A2/B1 push** — nl is the reference/most-mature language and
  is explicitly the first one expected to go deep; this gives a
  genuine intermediate-level PD source once nl's existing FSI Basic
  Course material is exhausted, at the cost of page-image reading
  (the existing FSI Basic Course, already in use, has real audio +
  the project's own note says 15/28 current nl units already draw from
  it — extraction quality of *that* existing source wasn't
  independently re-verified this pass, no reason to expect it's
  changed). **Skip Book IV's military-register content** when this is
  actually used.

### fa/prs: no new supplement found

Re-checked per the task's instructions but found nothing beyond what
`AUTHORING_GUIDE.md` §10 and root `CLAUDE.md`'s Secrets section already
document and have explicitly closed (FSI Persian Basic Course, Peace
Corps Dari, the DLI Dari Basic Course, and Intermediate Dari
ED131692 already covers the intermediate step). **Consistent with the
standing "don't re-investigate without new information" instruction**
for the Tatoeba pool — same logic applies here: no new information
surfaced, don't re-open. One tangential finding worth flagging for a
future *written* (not spoken) push: CERCLL's "Modern Persian: Written
and Spoken" advanced textbook series and the Routledge "Farsi Shirin
Ast" series both exist as real intermediate/advanced Persian courses,
but both are **commercially published, not PD or CC-licensed** —
categorically excluded per §10's "commercial textbooks" rule, noted
here only so a future search doesn't waste time re-discovering and
re-evaluating them.

---

## Per-language recommendation table

| Language | Best source for next authoring wave | License basis | Extraction mode | Realistic authoring mode |
|---|---|---|---|---|
| es (parked) | FSI Spanish Basic Course (§10, not re-verified) | PD | Unverified this pass | Adaptation (per §10) |
| fr (parked) | FSI French Basic Course (§10, not re-verified) | PD | Unverified this pass | Adaptation (per §10); COERLL Français interactif blocked on attribution infra |
| it | FSI Italian FAST, Vol 1–2 | PD | **Clean OCR text** (best in this pass) | Adaptation |
| ru | Yojik re-OCR'd "FSI Russian Fast Course" | PD (derivative re-typesetting of PD text) | **Clean OCR text incl. stress marks** (best non-Latin-script result) | Adaptation |
| zh | FSI Standard Chinese: A Modular Approach | PD | Scanned, zero text layer | Page-image reading (heaviest cost in this pass) |
| ro (unscoped) | Peace Corps "Survival Romanian" (clean, thin) + ED401768 pre-service manual (deep, scanned) | PD | Clean for #1, scanned for #2 | Adaptation for #1, page-image for depth |
| pl (unscoped) | FSI "Communicating in Polish" (clean) + DLI Polish Basic Course (deep, noisy OCR) | PD | Clean OCR for #1, noisy-but-usable OCR for #2 | Adaptation for both, extra proofreading for #2 |
| hi | FSI/Peace Corps "Hindi: An Active Introduction" | PD (dual FSI+Peace Corps) | Scanned, zero text layer (archive.org's CAL alternative has **actively wrong/garbage OCR** — avoid) | Page-image reading only |
| ar-eg (dialect, unapproved) | DLI Egyptian Arabic Basic Course (12 modules) | PD | Scanned, zero text layer | Page-image reading |
| ar-lev (dialect, unapproved) | FSI Levantine Arabic (tape-indexed, thin text) | PD | Scanned/audio-primary | Audio transcription + page-image, heavier than Egyptian |
| nl (supplement) | DLI Dutch Intermediate-Advanced Refresher (8 vols) | PD | Scanned, zero text layer | Page-image reading; skip Book IV's military register |
| fa/prs | No new source — §10 is current and closed | — | — | — |

## Top 3 discoveries this pass

1. **The yojik.eu community re-OCR'd Russian FSI Fast Course**
   (`yazik/Downloads/FSI-book-stressed.pdf`) — a full, clean, searchable
   Cyrillic PDF with stress marks intact, 370 pages, dramatically better
   than every other non-Latin-script source checked. Worth
   generalizing: before accepting a scanned FSI/DLI PDF as a dead end
   for any non-Latin-script language, check whether the yojik.eu/
   related community has a re-typeset "stressed"/"remade" version
   under a similarly-named alternate path (`yazik/` mirrors exist
   alongside the main `languages/FSI/` tree for at least Russian).
2. **The Devanagari archive.org OCR trap** (`HindiBasicCourse`) —
   trusting a "text layer present" signal without actually reading a
   sample of the extracted text produced total garbage (Latin-tuned
   Tesseract run against Devanagari pages). A real, previously
   undocumented failure mode, worse than a plain scanned dead-end
   because it looks superficially usable.
3. **DLI Dutch's Intermediate-Advanced Refresher Course** — a genuine,
   previously unmapped above-Basic-Course PD supplement for nl, the
   project's reference/most-mature language, ready for whenever nl's
   depth push reaches past what the current FSI Basic Course material
   covers (minus Book IV's military-register content, which should be
   skipped regardless of PD status).
