# Source map: Modern Standard Arabic (en↔ar)

Research pass for the newly-approved MSA learning path (MSA-first,
spoken-dialect track possibly later). Follows the standing sourcing
policy in `CLAUDE.md` ("Sourcing policy widened...") and
`docs/content/AUTHORING_GUIDE.md` §10 — public-domain FSI/DLI/Peace
Corps material tried first, CC-BY/CC0 treated as reference-only
(no attribution surface built yet), CC BY-SA and DLI GLOSS/Headstart2
categorically excluded.

**Firecrawl note**: `FIRECRAWL_API_KEY` is configured (authenticated
via stored credentials) but the account had **0/1,000 credits left
this cycle** at research time — every `firecrawl search`/`scrape` call
returned HTTP 402. Research below was done via `WebSearch`/`WebFetch`
plus direct `curl`/`pdftotext`/`pdfinfo` sampling instead (same
underlying material, just not routed through the firecrawl CLI as
instructed). Re-run this research through firecrawl once credits
refresh if a cleaner/faster extraction pass is wanted before the first
authoring dispatch — nothing below should change substantively, since
the actual source files and their scan quality are unaffected by which
tool reads them.

## Candidate sources

### 1. FSI Modern Written Arabic (Volumes 1–3) — MSA, primary candidate

- **URL**: `https://fsi-languages.yojik.eu/languages/FSI/fsi-written-arabic.html`
  (student texts: `Arabic/Written/Modern/Fsi-ModernWrittenArabic-Volume{1,2,3}-StudentText.pdf`,
  same host that already serves the project's active fa/nl FSI courses)
- **Covers**: MSA reading, writing, and spoken drill sentences. Vol 1:
  30 lessons + 2 reviews (a few individual lesson PDFs missing per the
  page's own note: 08, 10, 14, 15-1, 16-1, 23-1, 24-1 — text volume
  itself is complete, only some standalone lesson-audio-companion PDFs
  are gapped). Vol 2: 32 lessons (33–64), complete. Vol 3: text only,
  no stated lesson count found on the page. Despite the "Written"
  name, each lesson opens with "Basic Sentences" explicitly meant "to
  be read aloud," plus supplementary sentences, drills, grammar notes,
  and a running vocabulary — a real spoken+written course, not a pure
  literacy supplement. Level: FSI's own preface frames this as their
  main MSA track building toward newspaper/book reading; early lessons
  are genuine beginner material, appropriate as an A1 scaffold.
- **License/provenance**: `pdfinfo` on Vol 1 confirms `Author: Foreign
  Service Institute`, `Producer: Adobe Acrobat 8.12 Paper Capture
  Plug-in` (i.e. a real US State Department federal work, OCR-scanned
  for distribution) — same provenance basis already accepted for the
  project's fa/nl FSI courses (17 U.S.C. §105, no copyright on US
  federal government works). Genuinely public domain.
- **Extraction quality**: Mixed, sampled directly (`pdftotext -layout`
  on Vol 1, 434 pages). English front-matter/instructions/notes extract
  cleanly as real OCR text (readable, occasional OCR-artifact typos
  like "canprehension" for "comprehension" — normal for a 1960s scan).
  **The actual Arabic-script content is scanned-image-only — zero
  Arabic Unicode characters anywhere in a full-document extraction
  pass.** This is the same shape as the already-accepted Peace Corps
  Dari pattern (PDF-only, scanned, no splicing) — not disqualifying,
  but means authoring must use page-by-page image reading (the
  established fallback already used for scanned PD sources before the
  DLI Dari find), not clean text-copy from a scrape.
- **Audio**: Vol 1 and Vol 2 both have individual per-lesson MP3s
  (Vol 1: lessons 1–30 + reviews; Vol 2: lessons 33–64) hosted
  alongside the PDFs on the same site — real recorded native audio,
  useful the same way the project already uses FSI/DLI audio for fa/
  prs: a pronunciation-calibration reference for a human recording
  pass, not a splice-in-directly asset (per §10's standing "audio
  cannot be spliced directly" rule).
- **MSA vs dialect**: MSA.
- **Fitness verdict**: **Best available candidate for the first en→ar
  A1 wave.** Real structured lesson progression, real audio, genuine
  PD status, matches the project's existing FSI-adaptation playbook
  almost exactly — the only difference from fa/nl is that Arabic
  content must be read from page images rather than copy-pasted from
  clean OCR text, which is more authoring-dispatch effort per lesson
  but not a blocker.

### 2. DLI Arabic Basic Course (+ Cope, General Intermediate, SOLT) — MSA, secondary candidate

- **URL**: `https://fsi-languages.yojik.eu/languages/DLI/DLI-Arabic-general.html`
  — bundled archives only, no per-file directory listing (unlike the
  DLI Dari course, which listed 36 individual files):
  `archives/DLI-Arabic-Basic.tar.xz` (594 MB), plus `DLI-Arabic-Cope.tar.xz`,
  `DLI-Arabic-General-Intermediate.tar.xz`, `DLI-Arabic-MSA SOLT -
  Complete.zip`, and two `DLI-Headstart` archives (Arab World, East
  Asia — see caution below).
- **Covers**: The Basic Course archive (partially downloaded via HTTP
  range request, 30 MB sampled) contains at least 7 "Volume NN.pdf"
  student texts (Volume 07.pdf seen directly, implying a genuinely
  large multi-volume course, likely comparable in scope to the DLI
  Dari Basic Course's 40-lesson/3-semester structure) plus dozens of
  per-lesson MP3s (`lessonNNN-side 1/2.mp3`) and a "Sound and Script"
  pronunciation module. Site categorizes this as the general/MSA DLI
  track, distinct from the separately-hosted dialect-specific DLI
  courses (Syrian, Iraqi, Saudi, Egyptian — each its own page on the
  same site).
- **License/provenance**: DLI (Defense Language Institute Foreign
  Language Center) is a DoD component; its own-authored basic-course
  textbooks are the same category of federal work already accepted for
  the DLI Dari Basic Course precedent in `CLAUDE.md`. **Distinct from
  the categorically-excluded "DLI GLOSS/Headstart2"** (dliflc.edu-
  hosted lesson products with embedded third-party copyrighted news
  media, per AUTHORING_GUIDE §10) — this is the plain Basic
  Course/Cope/Intermediate/SOLT textbook set, not GLOSS.
- **Extraction quality**: Tested directly — extracted `Volume 07.pdf`
  from the partial archive download (240 pages, no embedded text
  layer at all: `pdftotext` output is 240 bytes total, effectively
  nothing, not even OCR'd front matter). **Fully scanned, no text
  layer whatsoever — worse than the FSI Written Arabic course**, which
  at least has OCR'd English instructions. Page-by-page image reading
  is the only extraction path.
- **Audio**: Substantial — many more per-lesson MP3s than the FSI
  course based on the partial listing sampled, same "pronunciation
  reference only" caveat as above.
- **MSA vs dialect**: MSA (site's own "general"/non-dialect-labeled
  categorization, consistent with how the Dari-equivalent course was
  categorized).
- **Caution — Headstart archives specifically**: `DLI-Arab-World.tar.xz`
  and `DLI-Arabic-Est-Asia.tar.xz` are literally named "Headstart" —
  close enough to the categorically-excluded "DLI GLOSS/Headstart2" to
  warrant NOT using them without a separate explicit content-audit
  confirming they don't embed third-party copyrighted media, same
  concern that got GLOSS/Headstart2 excluded in the first place. Not
  sampled this pass; treat as excluded-pending-verification, not
  cleared.
- **Fitness verdict**: Good secondary/backfill candidate for
  volume/depth once the FSI course's early units are exhausted — larger
  apparent lesson count and audio pool — but strictly worse extraction
  ergonomics (zero OCR at all vs. FSI's partial OCR) and the whole
  594 MB archive was never fully verified (only a 30 MB range sample);
  budget real time to fetch and enumerate the full archive before
  relying on a specific volume/lesson count. Basic/Cope/Intermediate/
  SOLT only — leave the two Headstart archives out.

### 3. Peace Corps Moroccan Arabic Textbook (2011 ed. / 1992 ED353812) — dialect, not MSA

- **URL**: `https://fsi-languages.yojik.eu/languages/PeaceCorps/Arabic-Moroccan/Moroccan Arabic Textbook - Student Edition.pdf`
  (also mirrored on `archive.org/details/MoroccanArabicTextbook2011`
  and indexed by ERIC as `ED353812`)
- **Covers**: Moroccan Arabic (Darija), 10 lessons — dialogue,
  vocabulary, grammar notes, a proverb, and supplementary dialogue per
  lesson. Topics: introductions, restaurant, general communication,
  transport, post office, shopping, talking about Peace Corps.
- **License/provenance**: US Peace Corps training material, same PD
  basis as the project's existing prs Peace Corps source.
- **Extraction quality**: Sampled directly — `pdfinfo` shows
  `Title: Print ED353812.TIF (199 pages)` (i.e. a straight TIFF-scan
  print job wrapped in a PDF) and `pdftotext` extracts essentially
  nothing (199 bytes total). Fully scanned, OCR-dead — same dead-end
  pattern as Peace Corps Dari.
- **MSA vs dialect**: **Dialect (Moroccan Darija)**, not MSA.
- **Fitness verdict**: Not usable for the MSA-first launch. Worth
  flagging for a future Maghrebi-dialect track, with the same
  page-image-reading caveat as above.

### 4. Peace Corps Jordan Pre-Departure Arabic Language Materials — dialect, not MSA

- **URL**: `https://files.peacecorps.gov/uploads/wws/lesson-plans/files/JO_Arabic_Language_Lessons.pdf`
  (also referenced from `peacecorps.gov/educators-and-students/
  educators/resources/arabic-jordan/`)
- **Covers**: 10 lessons of Jordanian-dialect pre-departure material —
  grammar notes, cultural notes, language-learning tips.
- **License/provenance**: US Peace Corps, same PD basis as above.
- **Extraction quality**: Not sampled this pass (found via search only,
  not downloaded/tested) — flag as unverified, but given the identical
  hosting pattern (`files.peacecorps.gov`, scanned training-manual
  style) to the confirmed-scanned Moroccan textbook and prs precedent,
  treat as likely scanned/OCR-dead until actually checked.
- **MSA vs dialect**: **Dialect (Jordanian/Levantine colloquial)**, not
  MSA.
- **Fitness verdict**: Not usable for the MSA-first launch; candidate
  for a future Levantine-dialect track alongside FSI's own Levantine
  Arabic course (`fsi-languages.yojik.eu/languages/FSI/fsi-levantine-
  arabic.html`, not sampled this pass — noted for completeness only,
  out of scope per this task's instructions).

### 5. Categorically excluded / out of scope, noted for completeness

- **DLI GLOSS / Headstart2** proper (dliflc.edu) — excluded per
  AUTHORING_GUIDE §10, unchanged. Also extends caution (not yet a hard
  exclusion) to the similarly-named `DLI-Headstart` archives under
  candidate #2 above — see that entry's caution note.
- **FSI Levantine Arabic**, **FSI Saudi Arabic**, **FSI Comparative
  Arabic** (Levantine/Egyptian comparative + Eastern-to-Western
  Arabic), **DLI Arabic Syrian/Iraqi/Saudi/Egyptian** — all real,
  apparently PD, but all dialect-specific. Not evaluated for
  extraction quality this pass since the task scope is MSA-first;
  worth a dedicated pass whenever a specific dialect track (most
  likely Egyptian or Levantine, per typical demand) gets approved.
- **Tatoeba / any CC-BY or CC0 source**: not separately re-investigated
  for Arabic this pass — per the standing §10 decision, CC-BY needs an
  attribution surface that doesn't exist yet and CC0 pools were
  previously found near-empty for every launch language; no reason to
  expect Arabic to differ materially, so this stays reference-only
  without a fresh measurement. Flag for a real CC0-pool-size check only
  if the FSI/DLI sources below turn out insufficient for depth.

## Recommendation

**Primary source for the first en→ar A1 authoring wave: FSI Modern
Written Arabic, Volume 1** (candidate #1). It has the best balance of
genuine PD status, a real structured beginner lesson progression with
audio, and at least partial clean-text extraction (English
instructional material OCRs cleanly, even though the Arabic itself
requires page-image reading) — the same adaptation shape already
proven out for fa (FSI Persian) and nl (FSI Dutch). Use the DLI Arabic
Basic Course (candidate #2, Basic/Cope/Intermediate/SOLT only, not the
Headstart archives) as the secondary/depth source once Volume 1's
~30 lessons are exhausted — it appears to have more raw lesson volume
and audio, at the cost of zero OCR at all (100% page-image reading, no
shortcuts).

**Corpus depth honesty for `generation_provenance`**: between FSI MWA's
3 volumes (~90+ lessons across written/spoken material) and DLI's
apparent 7+ volume Basic Course, there is very likely enough raw
source material to scaffold real MSA A1 (and probably well into A2)
content — comparable in apparent scale to the fa/nl precedents already
in active use. But **neither source was verified end-to-end this
pass** (FSI Vol 1 was sampled, not read lesson-by-lesson; the DLI
archive was only 5%-sampled via a partial download) — treat "the
corpus supports MSA A1" as a reasonable expectation, not a confirmed
fact, until a real authoring dispatch actually walks through Volume 1's
lessons page-by-page. Expect the same modernization burden §10 already
requires for fa/nl (1960s-70s register, dated cultural framing) applied
here too — no reason to think MSA-specific FSI/DLI material would be
exempt from that. No established-conventions gap-filling should be
needed for the first several A1 units given this source depth; revisit
if the page-by-page read reveals gaps (e.g. missing lesson PDFs already
flagged in Vol 1: 08, 10, 14, 15-1, 16-1, 23-1, 24-1).
