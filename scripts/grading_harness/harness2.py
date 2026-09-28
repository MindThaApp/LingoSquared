"""Run the REAL backend grade() over compiled content with realistic
learner-input perturbations of the canonical correct answer."""
import argparse, enum, importlib.util, json, sys, types, unicodedata, collections, pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description="Grade perturbations against compiled course JSON.")
parser.add_argument("--grading", type=pathlib.Path, default=REPO / "backend/app/review/grading.py")
parser.add_argument("--compiled-dir", type=pathlib.Path, required=True,
                    help="Directory of JSON files produced by compile_all.py")
args = parser.parse_args()

# --- stub app.core.errors / app.models so grading.py imports standalone
class HTTPErr(Exception):
    pass
def fail(status, code, message, **k):
    raise HTTPErr(code)
class ExerciseType(str, enum.Enum):
    flashcard = "flashcard"
app = types.ModuleType("app"); core = types.ModuleType("app.core")
errors = types.ModuleType("app.core.errors"); errors.fail = fail
models = types.ModuleType("app.models"); models.ExerciseType = ExerciseType
sys.modules.update({"app": app, "app.core": core, "app.core.errors": errors, "app.models": models})
spec = importlib.util.spec_from_file_location("grading", args.grading)
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

SCRIPTS = {"en":"latin","nl":"latin","fr":"latin","de":"latin","it":"latin","es":"latin","pl":"latin","ro":"latin",
           "ru":"cyrillic","zh":"han","ar":"arabic","fa":"arabic","prs":"arabic","ko":"hangul","ja":"japanese","hi":"devanagari"}

FREE = g.FREE_TEXT_EXERCISE_TYPES | {"fill_in_blank"}

def strip_terminal(s):
    t = s.rstrip()
    while t and unicodedata.category(t[-1]).startswith("P"):
        t = t[:-1].rstrip()
    return t
def strip_all_punct(s):
    return " ".join("".join(" " if unicodedata.category(c).startswith("P") and c not in "'’-" else c for c in s).split())
def smart_apos(s): return s.replace("'", "’")
def nfd(s): return unicodedata.normalize("NFD", s)
def hamza_fold(s):
    return s.translate(str.maketrans({"أ":"ا","إ":"ا","آ":"ا"}))
def one_typo(s):
    words = s.split()
    if not words: return None
    i = max(range(len(words)), key=lambda k: len(words[k]))
    w = words[i]
    letters = [k for k,c in enumerate(w) if c.isalpha()]
    if len(letters) < 5: return None
    k = letters[len(letters)//2]
    w2 = w[:k] + w[k+1:]  # single deletion
    words[i] = w2
    return " ".join(words)

PERTS = {
    "drop_terminal_punct": strip_terminal,
    "drop_all_punct": strip_all_punct,
    "smart_apostrophe": lambda s: smart_apos(s) if "'" in s else None,
    "nfd_decomposed": lambda s: nfd(s) if nfd(s) != s else None,
    "alef_hamza_folded": lambda s: hamza_fold(s) if hamza_fold(s) != s else None,
    "one_letter_typo": one_typo,
    "autocap_first": lambda s: (s[0].upper()+s[1:]) if s and s[0].islower() else None,
    "trailing_space_period": lambda s: s + "." if s and not unicodedata.category(s[-1]).startswith("P") else None,
}

stats = collections.defaultdict(collections.Counter)
examples = collections.defaultdict(list)
totals = collections.Counter()
for path in sorted(args.compiled_dir.glob("*.json")):
    data = json.loads(path.read_text())
    for course in data["courses"]:
        for unit in course["units"]:
            for lesson in unit["lessons"]:
                for ex in lesson["exercises"]:
                    et = ex["type"]
                    if et not in FREE: continue
                    cr = ex["correct_response"]
                    multi = g.is_multi_answer_response(cr)
                    canon = cr["canonical"] if multi else cr
                    if not isinstance(canon, str): continue
                    lang = ex["prompt"].get("answer_language_code")
                    script = SCRIPTS.get(lang)
                    fm = g.decode_feedback(ex.get("feedback"))
                    shape = "multi" if multi else "single"
                    totals[(et, shape)] += 1
                    for name, fn in PERTS.items():
                        resp = fn(canon)
                        if resp is None or resp == canon: continue
                        if multi and any(isinstance(a,str) and g.normalized(a)==g.normalized(resp) for a in cr["accepted"]):
                            # Author explicitly listed this variant; it is not a perturbation.
                            continue
                        try:
                            r = g.grade(resp, cr, et, script=script,
                                        orthography_strict=fm.get("orthography_strict"),
                                        case_sensitive=bool(fm.get("case_sensitive")),
                                        punctuation_strict=bool(fm.get("punctuation_strict")))
                        except HTTPErr as e:
                            r = "error"
                        key = (name, et, shape, script)
                        stats[key][r] += 1
                        if r == "incorrect" and et!="dictation" and len(examples[(name, lang)]) < 2 and name in ("autocap_first","smart_apostrophe","trailing_space_period","one_letter_typo"):
                            examples[(name, lang)].append((ex.get("content_key"), canon, resp))

print("TOTAL free-text exercises by (type, shape):")
for k, v in sorted(totals.items()): print("  ", k, v)
agg = collections.defaultdict(collections.Counter)
for (name, et, shape, script), c in stats.items():
    agg[(name, shape, script)].update(c)
print("\nPERTURBATION RESULTS (perturbation, shape, script): counts")
for k in sorted(agg): print("  ", k, dict(agg[k]))
print("\nPER-PERTURBATION TOTALS (correct / almost / incorrect):")
overall=collections.defaultdict(collections.Counter)
for (name, et, shape, script), c in stats.items():
    overall[name].update(c)
for name in PERTS:
    counts=overall[name]
    print(f"  {name}: correct={counts['correct']} almost={counts['almost']} incorrect={counts['incorrect']}")
print("\nBY TYPE (non-dictation):")
bt=collections.defaultdict(collections.Counter)
for (name, et, shape, script), c in stats.items():
    if et=="dictation": continue
    bt[(name, et, shape)].update(c)
for k in sorted(bt): print("  ", k, dict(bt[k]))
print("\nEXAMPLES graded incorrect:")
for k in sorted(examples):
    for e in examples[k]: print("  ", k, e)
