# Leaked-annotation gloss inventory (X-en) — generated 2026-07-30

Glosses whose Persian/Dari text embeds a raw English fragment inside `(…)`, reachable
as an MC option or translate prompt via a bare-POS slot (root: `_en_target_lexeme_common.py`
+ the two backfill dicts). This is the decision-ready inventory for the BATCH-8 data-layer
call in RAMIN_REVIEW_BACKLOG. **Not auto-fixed** — see the two classes below.

## fa_en — 158 leaked total
- **A. Disambiguating annotation (68)** — tense/3rd-person/contraction/negation/possessive. The English MUST go but a Persian marker MUST stay (else buy/bought, he/she collapse). Needs native delatinize, e.g. `خرید (زمان گذشتهٔ buy)` → `خرید (گذشته)`. Deploy-effect.
- **B. Standalone + cross-POS collision (52)** — base gloss alone re-exposes a shared gloss (well→خوب=good/fine/okay; get→رسیدن=arrive). Needs disambiguation, native. Deploy-effect.
- **C. Standalone + collision-free (38)** — base gloss appears self-sufficient & unique; candidate strip, but native spot-check that the base is a complete answer (e.g. کمی for 'little'). Deploy-effect.

<details><summary>C. collision-free candidates</summary>

- `a1` **board** (noun): `تخته (در diving board)` → `تخته`
- `a1` **broke** (verb): `خراب شد (در broke down)` → `خراب شد`
- `a1` **collection** (noun): `جمع‌آوری (در collection day)` → `جمع‌آوری`
- `a1` **diving** (noun): `شیرجه (در diving board)` → `شیرجه`
- `a1` **pick** (verb): `برداشتن (در pick up)` → `برداشتن`
- `a1` **runny** (adjective): `آبریزش‌دار (در runny nose)` → `آبریزش‌دار`
- `a2` **media** (noun): `رسانه (در social media)` → `رسانه`
- `a2` **staying** (verb): `در ارتباط ماندن (در staying in touch)` → `در ارتباط ماندن`
- `a2` **touch** (noun): `تماس (در in touch)` → `تماس`
- `b1` **able** (adjective): `توانا (در be able to)` → `توانا`
- `b1` **advance** (noun): `پیش (در in advance)` → `پیش`
- `b1` **best** (adjective): `بهترین (در do my best)` → `بهترین`
- `b1` **conference** (noun): `کنفرانس (در conference room)` → `کنفرانس`
- `b1` **depending** (verb): `بستگی داشتن (در depending on)` → `بستگی داشتن`
- `b1` **done** (verb): `انجام‌داده (قسمت سوم do)` → `انجام‌داده`
- `b1` **end** (noun): `آخر (در in the end)` → `آخر`
- `b1` **followed** (verb): `دنبال می‌شود (در followed by)` → `دنبال می‌شود`
- `b1` **known** (verb): `دانسته (قسمت سوم know)` → `دانسته`
- `b1` **left** (verb): `حذف کرد (در leave out)` → `حذف کرد`
- `b1` **order** (noun): `منظور (در in order to: برای این که)` → `منظور`
- `b1` **other's** (pronoun): `همدیگر (در each other's)` → `همدیگر`
- `b1` **person** (noun): `شخص (در in person: حضوری)` → `شخص`
- `b1` **pull** (verb): `کنار زدن (در pull over)` → `کنار زدن`
- `b1` **rather** (adverb): `ترجیحاً (در would rather)` → `ترجیحاً`
- `b1` **sign** (verb): `ثبت‌نام کردن (در sign up)` → `ثبت‌نام کردن`
- `b1` **signed** (verb): `ثبت‌نام کرد (در sign up)` → `ثبت‌نام کرد`
- `b1` **speech** (noun): `گفتار (در reported speech)` → `گفتار`
- `b1` **used** (verb): `عادت داشت (used to)` → `عادت داشت`
- `b1` **word** (noun): `قول (در keep one's word)` → `قول`
- `b2` **b** (symbol): `ب (نشانهٔ منبع B)` → `ب`
- `b2` **carry** (verb): `وزن داشتن (در carry weight)` → `وزن داشتن`
- `b2` **extent** (noun): `حد (در to some extent)` → `حد`
- `b2` **gone** (verb): `رفته (قسمت سوم go)` → `رفته`
- `b2` **moving** (verb): `پیش رفتن (در moving forward)` → `پیش رفتن`
- `b2` **passenger** (adjective): `مسافر (در passenger survey)` → `مسافر`
- `b2` **rules** (verb): `رد می‌کند (در rule out)` → `رد می‌کند`
- `b2` **setting** (verb): `در حال چیدن (در setting up)` → `در حال چیدن`
- `b2` **through** (preposition): `از ابتدا تا انتها (در walk through)` → `از ابتدا تا انتها`

</details>

## prs_en — 218 leaked total
- **A. Disambiguating annotation (111)** — tense/3rd-person/contraction/negation/possessive. The English MUST go but a Persian marker MUST stay (else buy/bought, he/she collapse). Needs native delatinize, e.g. `خرید (زمان گذشتهٔ buy)` → `خرید (گذشته)`. Deploy-effect.
- **B. Standalone + cross-POS collision (90)** — base gloss alone re-exposes a shared gloss (well→خوب=good/fine/okay; get→رسیدن=arrive). Needs disambiguation, native. Deploy-effect.
- **C. Standalone + collision-free (17)** — base gloss appears self-sufficient & unique; candidate strip, but native spot-check that the base is a complete answer (e.g. کمی for 'little'). Deploy-effect.

<details><summary>C. collision-free candidates</summary>

- `a1` **practicing** (verb): `تمرین کرده (شکل ing فعل practice)` → `تمرین کرده`
- `a1` **waiting** (verb): `انتظار کشیدن (شکل ing فعل wait)` → `انتظار کشیدن`
- `a1` **warms** (verb): `گرم می‌شه (در warm up)` → `گرم می‌شه`
- `a2` **Path** (proper_noun): `پَث (بخشی از نام شرکت Bright Path)` → `پَث`
- `b1` **despite** (preposition): `باوجود (+ اسم یا شکل -ing)` → `باوجود`
- `b1` **done** (verb): `کرده (شکل سوم فعل do)` → `کرده`
- `b1` **guessing** (verb): `حدس زدن (شکل ing فعل guess)` → `حدس زدن`
- `b1` **has already** (verb): `قبلاً ... کرده (زمان حال کامل با already)` → `قبلاً ... کرده`
- `b1` **known** (verb): `دانسته (شکل سوم فعل know)` → `دانسته`
- `b1` **leading** (verb): `رهبری کردن (شکل ing فعل lead)` → `رهبری کردن`
- `b1` **saving** (verb): `پس‌انداز کردن (شکل ing)` → `پس‌انداز کردن`
- `b1` **signed** (verb): `نام‌نویسی کرد (در sign up)` → `نام‌نویسی کرد`
- `b2` **arguing** (verb): `استدلال کردن (شکل ing فعل argue)` → `استدلال کردن`
- `b2` **conceding** (verb): `واگذار کردن (شکل ing فعل concede)` → `واگذار کردن`
- `b2` **lowering** (verb): `پایین آوردن (شکل ing فعل lower)` → `پایین آوردن`
- `b2` **missing** (verb): `نداشتن (شکل ing فعل miss)` → `نداشتن`
- `b2` **moving** (verb): `پیش رفتن (شکل ing فعل move)` → `پیش رفتن`

</details>
