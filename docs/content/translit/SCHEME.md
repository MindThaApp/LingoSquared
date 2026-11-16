# Pronunciation (romanization) schemes

Learner-friendly, pronunciation-oriented. NOT transliteration of spelling. One store per
target language (`docs/content/translit/<lang>.json`), independent of the learner's language.
Entry fields: `romanization`, `scheme`, `source` (rule | llm | human), `reviewed` (bool).
Key = normalised target string (see `scripts/translit/common.py::normalize_key`, mirrored in
`frontend/src/lib/translitKey.ts`).

General rules (all languages): lowercase except proper names (capitalised) and the first
word of a sentence is NOT capitalised; keep the source punctuation (`?`, `!`, `.`, `,`;
Arabic-script `؟ ،` become `? ,`); words separated by spaces; use a hyphen only where listed
below; no IPA, no stress marks unless listed.

## fa (Iranian Persian, spoken/colloquial register as written in the course)
Write what is SAID, not the spelling: `من می‌روم` as written -> still the written form's
pronunciation; colloquial spellings (`برم`, `خونه`) -> colloquial sound.
Vowels: a (short a, as in "cat"), â (long a, as in "father"), e, i (long ee), o (short, as
in "go"), u (long oo). Diphthongs: `ou` (nou, "new"), `ei` (kei, "when").
Consonants: kh (خ), gh (ق غ), sh, ch, zh (ژ), j (ج), ' for ع/ء only between vowels (optional,
prefer omission), y, v, h, plain letters otherwise.
The verb prefix mi- is hyphenated: `mi-ravam`, `mi-khâham`, `nemi-dânam`. Ezafe is written
`-e` (`ketâb-e man`); after a vowel `-ye` (`khâne-ye man`). Clitic `râ` stays separate
(`ketâb râ`, colloquial `ketâb o`). Examples: salâm, khodâ hâfez, man mi-ravam, khâne, ketâb.

## prs (Dari, Afghanistan)
Same scheme as fa, but Dari pronunciations: keep ē (ی-majhul, `shēr` lion) and ō (و-majhul,
`khōb` good) where Dari distinguishes them; `â` is pronounced closer to o but still written
`â`; ا at word edges as in fa. Dari lexical/verbal forms as written in the course
(`mē-rawam`, `khâna`, `kitâb`). Use the same hyphen/ezafe rules (`mē-rawam`, `kitâb-e man`).
Only these diacritics are used: â ē ō (never ā ī ū).

## ar (Modern Standard Arabic; course text is unvowelled)
Supply the short vowels the spelling omits, using the standard pausal reading (no case
endings except where fixed phrases carry them). Long vowels: ā ī ū. Short: a i u.
Consonants: th (ث), j (ج), ḥ -> h, kh, dh (ذ), sh, ṣ->s, ḍ->d, ṭ->t, ẓ->z (no dots: learner
style), gh, q (ق), ' for hamza/ʿayn -> hamza `'`, ʿayn `'` too (single apostrophe, only
mid/final), w, y. Definite article `al-` before moon letters and assimilated before sun
letters in speech (`ash-shams`), hyphenated: `al-kitāb`, `ash-shams`. Examples: māl,
marḥaban -> marhaban, shukran, as-salāmu 'alaykum.

## ru (rule-based, BGN/PCGN-simplified)
а a, б b, в v, г g, д d, е ye (word-initial / after vowel / after ь ъ) else e, ё yo, ж zh,
з z, и i, й y, к k, л l, м m, н n, о o, п p, р r, с s, т t, у u, ф f, х kh, ц ts, ч ch,
ш sh, щ shch, ъ (omitted), ы y, ь omitted,
э e, ю yu, я ya. No stress marks (unavailable in source). Examples: zhizn, shchi, privyet.

## hi (rule-based with schwa deletion)
Hunterian-style everyday spelling. `a` is the inherent vowel; word-final schwa and
medial schwa (in the VC.CV pattern) are deleted: घर ghar, कमल kamal, नमस्ते namaste.
long vowels आ ई ऊ -> `aa`, `ee`, `oo` inside a word, but word-final `aa` -> `a` and `ee` -> `i` (priya, hindi, ka); ए e, ऐ ai, ओ o, औ au; ऋ ri; nasal ं/ँ -> n (or
`n` before consonant); visarga ः -> h. Aspirates: kh gh ch jh th dh ph bh; retroflex and
dental not distinguished (t, d); nukta forms: क़ q, ख़ kh, ग़ gh, ज़ z, ड़ r, ढ़ rh, फ़ f. ज्ञ gya,
श sh, ष sh. Examples: namaste, mujhe sir dard hai, dhanyavaad.
