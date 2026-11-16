"""Rule-based romanizers (ru, hi) following docs/content/translit/SCHEME.md.

The hi engine is derived from scripts/derive_target.py::translit_hi_word (slug-only) with
learner-grade vowel lengths, a proper right-to-left schwa-deletion pass and an exception list.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------- ru
_RU = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ё": "yo",
}
_RU_VOWELS = set("аеёиоуыэюя")
_RU_EXC = {
    "что": "shto", "чтобы": "shtoby", "его": "yevo", "сегодня": "sevodnya", "здравствуйте": "zdravstvuyte",
    "здравствуй": "zdravstvuy", "конечно": "konyeshno", "скучно": "skushno", "вот": "vot", "это": "eto",
    "кто": "kto", "мой": "moy", "твой": "tvoy", "ее": "yeyo", "её": "yeyo", "их": "ikh",
}


def ru_word(w: str) -> str:
    low = w.lower()
    if low in _RU_EXC:
        r = _RU_EXC[low]
        return r.capitalize() if w[0].isupper() else r
    out = []
    for i, ch in enumerate(w):
        lc = ch.lower()
        if lc == "е":
            prev = w[i - 1].lower() if i else ""
            r = "ye" if (i == 0 or prev in _RU_VOWELS or prev in "ьъ") else "e"
        elif lc in _RU:
            r = _RU[lc]
        else:
            r = ch
        if ch != lc and r:  # uppercase source letter
            r = r[0].upper() + r[1:]
        out.append(r)
    return "".join(out)


def ru(text: str) -> str:
    text = text.replace("́", "")  # stress mark, if any
    return re.sub(r"[Ѐ-ӿ]+(?:-[Ѐ-ӿ]+)*", lambda m: "-".join(ru_word(p) for p in m.group(0).split("-")), text)


# ---------------------------------------------------------------- hi
_CONS = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
         "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
         "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
         "ष": "sh", "स": "s", "ह": "h", "ळ": "l"}
_PRECOMP_NUKTA = {"क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f", "य़": "y"}
_NUKTA = {"क": "q", "ख": "kh", "ग": "gh", "ज": "z", "फ": "f", "ड": "r", "ढ": "rh"}
_VOW = {"अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o",
        "औ": "au", "ऑ": "o"}
_MATRA = {"ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
          "ॉ": "o", "ॅ": "e"}
_DIGITS = {ord(c): str(i) for i, c in enumerate("०१२३४५६७८९")}
HI_EXCEPTIONS = {
    "नहीं": "nahin", "मैं": "main", "में": "mein", "हैं": "hain", "हूँ": "hoon", "हूं": "hoon", "है": "hai",
    "यह": "yah", "वह": "vah", "कौन": "kaun", "कहाँ": "kahaan", "यहाँ": "yahaan", "वहाँ": "vahaan", "क्यों": "kyon",
    "क्या": "kya", "आप": "aap", "हम": "hum", "तुम": "tum", "मुझे": "mujhe", "तुझे": "tujhe", "उसे": "use",
    "उन्हें": "unhein", "उन्हें": "unhen", "इन्हें": "inhen", "कुछ": "kuchh", "कृपया": "kripaya", "धन्यवाद": "dhanyavaad",
    "नमस्ते": "namaste", "नमस्कार": "namaskaar", "शुक्रिया": "shukriya", "अच्छा": "achchha", "अच्छी": "achchhi",
    "अच्छे": "achchhe", "ठीक": "theek", "बहुत": "bahut", "सब": "sab", "और": "aur", "या": "ya", "पर": "par",
    "को": "ko", "का": "ka", "की": "ki", "के": "ke", "से": "se", "ने": "ne", "भी": "bhi", "ही": "hi", "तो": "to",
    "जी": "jee", "हाँ": "haan", "ना": "na", "घर": "ghar", "भारत": "bhaarat", "हिंदी": "hindi", "हिन्दी": "hindi",
    "अंग्रेज़ी": "angrezi", "अंग्रेजी": "angrezi", "पानी": "paani", "खाना": "khaana", "चाय": "chaay",
    "आज": "aaj", "कल": "kal", "अब": "ab", "जब": "jab", "तब": "tab", "कब": "kab", "कैसे": "kaise", "कैसा": "kaisa",
    "कैसी": "kaisi", "कितना": "kitna", "कितने": "kitne", "कितनी": "kitni", "मेरा": "mera", "मेरी": "meri",
    "मेरे": "mere", "तुम्हारा": "tumhaara", "आपका": "aapka", "आपकी": "aapki", "आपके": "aapke", "उसका": "uska",
    "रहा": "raha", "रही": "rahi", "रहे": "rahe", "था": "tha", "थी": "thi", "थे": "the", "गया": "gaya",
    "गयी": "gayi", "गई": "gayi", "गए": "gaye", "गये": "gaye",
}


def _units(w: str):
    units: list[list] = []  # [text, kind]  C inherent-a consonant, c vowelless consonant, V vowel, N nasal/visarga
    i = 0
    while i < len(w):
        ch = w[i]
        pair = w[i : i + 2]
        if pair in _PRECOMP_NUKTA or (ch in _CONS and i + 1 < len(w) and w[i + 1] == "़"):
            if pair in _PRECOMP_NUKTA:
                units.append([_PRECOMP_NUKTA[pair], "C"])
            else:
                units.append([_NUKTA.get(ch, _CONS[ch]), "C"])
            i += 2 if (pair in _PRECOMP_NUKTA or w[i + 1] == "़") else 1
            continue
        if ch in _CONS:
            units.append([_CONS[ch], "C"])
        elif ch in _MATRA and units:
            units[-1][1] = "c"
            units.append([_MATRA[ch], "V"])
        elif ch == "्" and units:
            units[-1][1] = "c"
        elif ch in "ँं":
            units.append(["n", "N"])
        elif ch == "ः":
            units.append(["h", "N"])
        elif ch in _VOW:
            units.append([_VOW[ch], "V"])
        elif ch == "़":
            pass
        elif ch == "‍" or ch == "‌":
            pass
        else:
            units.append([ch, "X"])
        i += 1
    return units


def hi_word(w: str) -> str:
    if w in HI_EXCEPTIONS:
        return HI_EXCEPTIONS[w]
    u = _units(w)
    n = len(u)
    keep = [k == "C" for _, k in u]  # inherent a retained?
    # last consonant carrying a schwa (ignoring trailing nasals) is deleted
    last = max((j for j in range(n) if u[j][1] in "CcVX"), default=-1)
    for j in range(n - 1, -1, -1):
        if u[j][1] != "C":
            continue
        if j == last:
            keep[j] = False
            continue
        if j == 0:
            continue
        prev_has_vowel = (
            u[j - 1][1] == "V"
            or (u[j - 1][1] == "C" and keep[j - 1])
            or (u[j - 1][1] == "N" and j >= 2 and u[j - 2][1] == "V")
        )
        if not prev_has_vowel:
            continue
        nxt = u[j + 1] if j + 1 < n else None
        if nxt is None:
            continue
        if nxt[1] == "V":
            nv = True
        elif nxt[1] == "C":
            nv = keep[j + 1]
        elif nxt[1] == "c":
            nv = j + 2 < n and u[j + 2][1] == "V"
        else:
            nv = False
        if nv:
            keep[j] = False
    out = []
    for j, (t, k) in enumerate(u):
        out.append(t + ("a" if k == "C" and keep[j] else ""))
    r = "".join(out)
    # word-final long aa / ee are written short (kitaab, but ka, priya, hindi)
    r = re.sub(r"aa$", "a", r)
    r = re.sub(r"ee$", "i", r)
    return r


def hi(text: str) -> str:
    text = text.translate(_DIGITS).replace("।", ".").replace("॥", ".").replace("。", ".")
    return re.sub(r"[ऀ-ॿ]+", lambda m: hi_word(m.group(0)), text)
