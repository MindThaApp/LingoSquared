# Dari register repair — `prs-en` overlay lane

**Status:** active repair, opened 2026-07-22. Defect class **1.28 (Dari
dialect split-brain)** in `docs/CONTENT_DEFECT_REGISTRY.md`.

## The defect

`docs/content/overlays/prs-en/` A1 units 01–24 were authored in **Iranian
Persian register, not Dari**, and are partly copy-identical to
`docs/content/overlays/fa-en/` — 944 byte-identical Perso-Arabic strings.
A2 and B2 carry the same signature more weakly; B1 is formal-drifted but
not copied. Units 30–68 are correct (94–99% Dari copula) and are the
reference exemplars.

This lands on the first two units a Dari learner ever sees, and it is
**already deployed** to the live server.

| band | strings | identical to fa-en | dup % | Dari-copula share |
|---|---|---|---|---|
| a1 u01–02 | 244 | 95 | 39.0% | 34% |
| a1 u03–24 | 2829 | 796 | 28.1% | 13% |
| **a1 u30–44** | 1466 | 162 | 11.1% | **94%** ← good |
| **a1 u45–68** | 2494 | 160 | 6.4% | **99%** ← good |
| a2 u25–34 | 917 | 133 | 14.4% | 19% |
| b1 u01–19 | 1934 | 130 | 6.7% | 10% |
| b2 u01–08 | 868 | 34 | 3.9% | 19% |

## Absolute rules

1. **NEVER open `docs/content/overlays/fa-en/` or `docs/content/realizations/fa/`.**
   Treat the fa lane as if it does not exist. "For reference only" has
   failed twice in this project. Your Dari exemplars are
   `overlays/prs-en/a1_unit45.yaml` and `a1_unit56.yaml`, plus
   `docs/content/realizations/prs/`.
2. **Edit VALUES only. Never rename, add, or delete a YAML key** — the
   keys are `content_key`s and the overlay join breaks if they move.
   This also means user progress and SRS rows survive the repair.
3. **`docs/content/AUTHORING_GUIDE.md` is binding.** Read it.
4. Do not touch `docs/content/realizations/en/` — it is the shared English
   corpus consumed by four directions.

## The crux: legitimate overlap vs genuine defect

Dari and Iranian Persian genuinely share most core vocabulary. **An
over-broad find/replace would corrupt correct content.**

The discriminator is length plus register. In the known-good band, 77% of
strings shared with fa-en are ≤2 words — bare vocabulary glosses
(`نقاشی`, `فوتبال`, `تنیس`), legitimately identical. In the defective
bands only 42% are ≤2 words, and **288 are ≥6-word sentences** of
instructional prose. Long shared prose is the defect; short shared
vocabulary usually is not.

## Mapping table (corpus-verified)

### Copula — the class 1.28 core
`است`→`استه` · `هست`→`استه` · `هستم`→`استم` · `هستید`→`استین` ·
`هستیم`→`استیم` · `هستند`→`استند`

⚠️ **Scope note:** `است` is *correct* in `realizations/prs/` (3,601
uses — formal written Dari). The pin applies to the **`prs-en` overlay
lane**, which `docs/content/CLAUDE.md` fixes as *colloquial* Dari.

### 2pl `-ید` → `-ین`
`کنید`→`کنین` · `بنویسید`→`بنویسین` · `بگویید`→`بگویین` ·
`بدهید`→`بتین` · `دارید`→`دارین` · `بفرمایید`→`بفرمایین` ·
`می‌توانید`/`می‌تونید`→`می‌تانین`

### Formal 3sg `-د` → colloquial `-ه` (prs-en overlay lane only)
`می‌کند`→`می‌کنه` · `می‌گوید`→`می‌گه` · `می‌شود`→`می‌شه` ·
`می‌پرسد`→`می‌پرسه` · `می‌آید`→`می‌آیه` · `می‌رود`→`می‌ره`

### Tehrani contractions — no Dari counterpart, always wrong here
`یه`→`یک` · `اون`→`او`/`آن` · `اونجا`/`اونا` · `کدوم`→`کدام` ·
`همون`→`همو` · `خونه`→`خانه` · `نشون`/`تموم`/`کتابخونه` ·
`می‌تونم`→`می‌تانم` · `می‌خوام`→`می‌خواهم` · `می‌دونم`→`می‌دانم` ·
`چیه`/`کیه` · `بهت`/`بهم`/`ازش`/`توش`/`باهاش` · `آره`/`بله`→`بلی` ·
`مرسی`→`تشکر` · `بهتره` · `میاد`→`می‌آیه`

### Lexical — HARD (0 occurrences in any known-good band, safe to enforce)
`دانش‌آموز`→`شاگرد`/`محصل` · `آموزگار`→`معلم` (note the direction:
`معلم` is the Afghan word, `آموزگار` the Iranian coinage) ·
`خیابان`→`سرک` · `اتوبوس`→`بس` · `دلار`→`دالر` ·
`تومان`/`تومن`/`ریال`→`افغانی` · `خشکشویی`→`رخت‌شویی` ·
`فروشگاه`→`دوکان` · `فیلم`→`فلم`

### Lexical — ADVISORY ONLY, do NOT auto-replace
A more-Afghan word exists, but the Iranian one is already **taught
content** elsewhere in the corpus. Changing these breaks exercises:

`دانشگاه`/`پوهنتون` · `مدرسه`/`مکتب` · `داروخانه`/`دواخانه` ·
`مغازه`/`دوکان` · `دکتر`/`داکتر` · `هتل`/`هوتل` · `موزه`/`موزیم` ·
`استخر`/`حوض` · **`بلیط`/`تکت`** (`بلیط` is used 422× as taught
vocabulary — a blind replace breaks dozens of exercises) ·
`دوچرخه`/`بایسکل` · `مهندس`/`انجنیر` · `کیف`/`بکس` · `قطار` · `چتر`

### Instructional metalanguage (prs-en overlay lane norm)
`پاسخ`→`جواب` · `پرسش`→`سوال` · `واژه‌ها`→`کلمه‌ها` ·
`مخاطب`→`طرف مقابل` · `طبق`→`مطابق`

## NOT defects — do not "fix" these

- The colloquial `-ه` 3sg clitic: `می‌کنه`, `می‌شه`, `می‌گه`, `خوبه`.
  Kabuli Dari does this too.
- `اگه`, `باشه`, `بریم`, `برم`, `همدیگه`.
- `می‌خواهم` / `می‌خواهد` / `می‌تواند` — **full uncontracted forms are
  the Dari norm** (`می‌خواهم` appears 595× in `realizations/prs`).
- Short (≤2 word) vocabulary glosses that happen to match fa.

## Verification (every batch must pass all four)

1. `.content-venv/bin/python scripts/check_dari_register.py` → **zero
   findings for your files**. This detector was written for this defect
   and is calibrated to 0 false positives on the known-good bands.
2. `.content-venv/bin/python scripts/compile_content.py validate` for the
   affected chain → **0 errors** (see `scripts/verify.sh` for the exact
   invocation, `scripts/content_manifest.txt` for the chains).
3. Grading-field care: **64 strings sit in graded fields**
   (`correct_option`, `distractors`, `accepted_answers.value`,
   `pairs.left`), almost all in A1 u01–24. Changing one of these can make
   a correct learner answer fail. The coordinator runs
   `backend/tests/test_content_answer_shapes.py` centrally.
4. A separate fresh-context review per batch — this is launch-gate
   content, full review, no sampling (root `CLAUDE.md` tiered-review
   policy).
