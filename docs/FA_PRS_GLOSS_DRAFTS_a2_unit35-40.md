# fa/prs a2_unit35–40 gloss DRAFTS — for native review (2026-08-02)

> ⚠️ **These are UNVERIFIED best-effort drafts produced by Claude (not a native
> Farsi/Dari speaker).** They exist to give a native reviewer a *head-start* — confirm
> or correct each cell before it is wired into `backfill_lexemes_{fa,prs}_en.py`.
> **A wrong gloss ships as the graded "correct" answer**, so nothing here goes live
> until a native signs off. Each gloss must match the **taught sense** (the English
> context column), the lane register (fa-en = colloquial spoken Persian; prs-en =
> colloquial Dari), and use native numerals for symbol tokens.
>
> **🔴 = Farsi and Dari plausibly DIVERGE here — reviewer, look closely.**
> **conf = my confidence (H/M/L).** Low-confidence rows need the most attention.

## a2_unit35 · prescription

| token | taught sense | Farsi draft (fa-en) | Dari draft (prs-en) | conf | note |
|---|---|---|---|---|---|
| dose | amount of medicine to take | دوز / مقدار مصرف | دوز / اندازهٔ دوا | M | "دوز" is the loanword both use; Dari may prefer "اندازهٔ دوا" |
| refill | a repeat/renewal of a prescription | تجدید نسخه | تجدید نسخه | M | is "تجدید" natural here, or "تکرار نسخه"? |
| side | the "side" in **side effects** only | جانبی (در «عوارض جانبی») | جانبی (در «عوارض جانبی») | M | bare "side" — only meaningful inside عوارض جانبی |
| effects | (side) effects of medicine | عوارض | عوارض | M | |
| shouldn't | should not (negative advice) | نباید | نباید | H | |
| refills | plural — prescription refills | تجدیدهای نسخه | تجدیدهای نسخه | L | 🔴 awkward as a plural noun — reviewer please fix the natural form |

## a2_unit36 · document_correction

| token | taught sense | Farsi draft | Dari draft | conf | note |
|---|---|---|---|---|---|
| certificate | an official document/certificate | گواهی | تصدیق | M | 🔴 Dari commonly uses **تصدیق**; Farsi **گواهی/سند** |
| spelled | past/participle of *spell* | هجی‌شده | املا‌شده | L | 🔴 spelling verb differs; confirm both |
| copy | a duplicate of a document (noun) | کپی / رونوشت | کاپی / نقل | M | 🔴 Dari "کاپی/نقل"; Farsi "کپی/رونوشت" |
| passport | passport | گذرنامه / پاسپورت | پاسپورت | M | Farsi formal گذرنامه; Dari پاسپورت |
| mistakes | plural — errors in a document | اشتباهات / خطاها | اشتباهات / غلطی‌ها | M | |
| registration | registration (certificate/office) | ثبت‌نام | راجستر / ثبت | L | 🔴 Dari often "راجستر"; confirm |
| correction | a correction (act/result) | تصحیح / اصلاح | تصحیح / اصلاح | M | |
| corrected | past participle of *correct* | تصحیح‌شده / اصلاح‌شده | تصحیح‌شده / اصلاح‌شده | M | |
| reference | reference (as in reference number) | مرجع / رفرنس | مرجع / رفرنس | M | in "شمارهٔ مرجع" |
| 3092 | a reference number (symbol) | ۳۰۹۲ | ۳۰۹۲ | H | native-numeral rendering only |

## a2_unit37 · video_calls

| token | taught sense | Farsi draft | Dari draft | conf | note |
|---|---|---|---|---|---|
| microphone | microphone | میکروفون | میکروفون | H | |
| connection | network/internet connection | اتصال / ارتباط | ارتباط / کنکشن | M | 🔴 Dari may use "کنکشن"; confirm |
| mute | to mute (a microphone) | بی‌صدا کردن | خاموش کردن صدا / بی‌صدا کردن | M | colloquial form? |
| face | the "face" in **face to face** only | رو (در «رو‌در‌رو») | رو (در «رو‌در‌رو») | L | 🔴 bare "face" is only the idiom رودررو — reviewer confirm the gloss shape |
| calls | plural — **video calls** (noun) | تماس‌ها (تماس تصویری) | تماس‌ها (تماس تصویری) | M | not phone calls, not the verb |
| headphones | headphones | هدفون | هدفون | H | |
| asks | 3rd-person sing. of *ask* | می‌پرسه | می‌پرسه / می‌پرسد | M | colloquial-fa register per lane pin |
| question | a question | سوال | سوال | H | |
| classmates | fellow students | هم‌کلاسی‌ها | هم‌صنفی‌ها | M | 🔴 Dari uses **صنف** → هم‌صنفی; Farsi هم‌کلاسی |
| speaking | present participle of *speak* | حرف زدن / صحبت کردن | گپ زدن / صحبت کردن | M | 🔴 Dari colloquial "گپ زدن" |

## a2_unit38 · repair_visit

| token | taught sense | Farsi draft | Dari draft | conf | note |
|---|---|---|---|---|---|
| leak | a water leak | نشتی / چکه | چکک / نشت | M | 🔴 Dari "چکک"; Farsi "نشتی" |
| won't | will not | نمی‌... / نخواهد | نمی‌... / نخواهد | M | tense form depends on frame |
| rescheduled | past/participle of *reschedule* | دوباره وقت‌دهی شده / زمانش عوض شده | وقتش تغییر کرده | L | 🔴 no single word — confirm the natural phrase |
| 9am | clock time 9:00 morning (symbol) | ۹ صبح | ۹ صبح | H | native-time rendering |
| 11am | clock time 11:00 morning (symbol) | ۱۱ صبح | ۱۱ صبح | H | native-time rendering |

## a2_unit39 · after_the_interview

| token | taught sense | Farsi draft | Dari draft | conf | note |
|---|---|---|---|---|---|
| contract | an employment contract | قرارداد | قرارداد | H | |
| salary | salary/pay | حقوق / معاش | معاش | M | 🔴 Dari commonly **معاش**; Farsi حقوق |
| accept | to accept (a job/position) | پذیرفتن / قبول کردن | قبول کردن | M | |
| interested | interested (in a job) | علاقه‌مند / مایل | علاقه‌مند / علاقه‌داشتن | M | |

## a2_unit40 · online_order_problem

| token | taught sense | Farsi draft | Dari draft | conf | note |
|---|---|---|---|---|---|
| delivery | a delivery (of goods) | تحویل / ارسال | تسلیمی / رسانش | L | 🔴 Dari differs a lot; confirm |
| parcel | a parcel/package | بسته | بسته / پارسل | M | |
| lamp | a lamp (the ordered item) | چراغ / لامپ | چراغ / لامپ | M | |
| 8154 | an order number (symbol) | ۸۱۵۴ | ۸۱۵۴ | H | native-numeral rendering only |

---

## How to use the confirmed sheet
Once a native fills/corrects every cell:
1. Add each token to `FA_EN_EXTRA_LEXEMES` (fa-en) as `"token": ("pos", "‹farsi›")`
   and to the prs-en gloss dict as `"token": "‹dari›"`, grouped under
   `# --- a2 unitNN: <title> ---`, matching the existing entry format.
2. Run the two backfills, author the 12 packs (6 per direction, mirror the nl-en
   a2_unit35-40 wave), register in `practice_manifest.txt`, import, and the 12
   checkpoints flip available. See `docs/FA_PRS_GLOSS_WORKLIST_a2_unit35-40.md` for
   the POS/format details and `docs/LAUNCH_GATE_PUBLISH_READINESS_2026-08-02.md` for
   why these are the last launch blocker.
