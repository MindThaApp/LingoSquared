#!/usr/bin/env python3
"""LLM-draft romanizations for ar/fa/prs via parallel `codex exec` jobs (reviewed=false).

Work dir (drafts, batches, logs) lives OUTSIDE the repo (--work); results are merged into
docs/content/translit/<lang>.json with `merge`. Never overwrites entries with source human/rule
or reviewed=true.

  llm_draft.py run   --lang fa --work DIR [--batch 120] [--jobs 6] [--limit N] [--model M]
  llm_draft.py merge --lang fa --work DIR
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from translit.common import REPO, collect_target_strings, latin_ok, load_store, save_store  # noqa: E402

SCHEME_DOC = (REPO / "docs/content/translit/SCHEME.md").read_text(encoding="utf-8")

SECTION = {"ar": "## ar", "fa": "## fa", "prs": "## prs"}
LANG_NAME = {"ar": "Modern Standard Arabic", "fa": "Iranian Persian (Farsi)", "prs": "Dari (Afghan Persian)"}


def scheme_for(lang: str) -> str:
    parts = re.split(r"(?m)^## ", SCHEME_DOC)
    general = parts[0]
    mine = [p for p in parts[1:] if p.startswith(lang + " ")]
    extra = ""
    if lang == "prs":
        extra = "".join("## " + p for p in parts[1:] if p.startswith("fa "))
    return general + "".join("## " + p for p in mine) + ("\n(For reference, the fa scheme it builds on:)\n" + extra if extra else "")


def prompt_for(lang: str, rows: list[tuple[int, str]]) -> str:
    body = "\n".join(f"{i}\t{t}" for i, t in rows)
    return f"""You are drafting learner-friendly pronunciation romanizations for {LANG_NAME[lang]} course text.
Follow this scheme EXACTLY and consistently:

{scheme_for(lang)}

Task: for each input line `id<TAB>text`, output one line `id<TAB>romanization`. Same ids, same order,
one line per input, nothing else (no explanations, no code fences, no header). Do not run any
commands and do not read or write files; just answer in your final message. Romanize what a
native speaker would SAY (supply short vowels the script omits). Keep numbers/Latin as is.
Keep the sentence's own punctuation (convert Arabic-script punctuation to ? , ; ). Proper names
are capitalised.

INPUT:
{body}
"""


def parse_output(text: str, rows):
    want = {i: t for i, t in rows}
    got: dict[int, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*(\d+)\t(.+?)\s*$", line)
        if m and int(m.group(1)) in want:
            r = m.group(2).strip()
            if latin_ok(r):
                got[int(m.group(1))] = r
    return got


def run_job(lang, rows, work: Path, tag: str, model: str | None) -> dict[int, str]:
    for attempt in range(4):
        got = _run_job_once(lang, rows, work, tag, model)
        if got:
            return got
        log = (work / "jobs" / tag / "log.txt")
        text = log.read_text(errors="ignore") if log.exists() else ""
        if "usage limit" in text or limited(work):
            return {}
        time.sleep(60 * (attempt + 1))  # 429 / transient: back off and retry
    return {}


def _run_job_once(lang, rows, work: Path, tag: str, model: str | None) -> dict[int, str]:
    jd = work / "jobs" / tag
    jd.mkdir(parents=True, exist_ok=True)
    (jd / "prompt.txt").write_text(prompt_for(lang, rows), encoding="utf-8")
    out = jd / "out.txt"
    cmd = ["codex", "exec", "-s", "read-only", "--skip-git-repo-check", "-C", str(jd), "-o", str(out),
           "-c", 'model_reasoning_effort="low"']
    if model:
        cmd += ["-m", model]
    cmd += ["-"]
    try:
        with open(jd / "prompt.txt", "rb") as stdin, open(jd / "log.txt", "wb") as log:
            subprocess.run(cmd, stdin=stdin, stdout=log, stderr=subprocess.STDOUT, timeout=900)
    except subprocess.TimeoutExpired:
        return {}
    if not out.exists():
        return {}
    return parse_output(out.read_text(encoding="utf-8"), rows)


def limited(work: Path) -> bool:
    return (work / "STOP").exists()


def cmd_run(a):
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    drafts_p = work / f"{a.lang}.drafts.jsonl"
    done: dict[str, str] = {}
    if drafts_p.exists():
        for line in drafts_p.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            done[d["k"]] = d["r"]
    store = load_store(a.lang)
    counts = collect_target_strings(a.lang)
    todo = [k for k in counts if k not in done and k not in store["entries"]]
    # frequent first, then short first (words/short phrases cover the most ground)
    real = collect_target_strings(a.lang, ("realizations", "practice"))
    todo.sort(key=lambda k: (k not in real, -counts[k], len(k), k))
    if a.limit:
        todo = todo[: a.limit]
    print(f"{a.lang}: {len(counts)} strings, {len(done)} drafted, {len(todo)} to do", flush=True)
    batches = [todo[i : i + a.batch] for i in range(0, len(todo), a.batch)]
    lock = threading.Lock()
    fails = {"n": 0}

    def work_one(idx_batch):
        idx, batch = idx_batch
        if limited(work):
            return
        rows = list(enumerate(batch))
        got = run_job(a.lang, rows, work, f"{a.lang}-{idx:05d}", a.model)
        if not got:
            with lock:
                fails["n"] += 1
                if "usage limit" in (work / "jobs" / f"{a.lang}-{idx:05d}" / "log.txt").read_text(errors="ignore"):
                    (work / "STOP").write_text("codex usage limit hit\n")
                if fails["n"] >= a.max_fails:
                    (work / "STOP").write_text("too many failed jobs (limit hit?)\n")
            return
        with lock, open(drafts_p, "a", encoding="utf-8") as f:
            for i, r in got.items():
                f.write(json.dumps({"k": batch[i], "r": r}, ensure_ascii=False) + "\n")
        print(f"batch {idx}: {len(got)}/{len(batch)}", flush=True)

    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        list(ex.map(work_one, enumerate(batches)))
    print("finished", flush=True)


def cmd_merge(a):
    work = Path(a.work)
    store = load_store(a.lang)
    store.setdefault("lang", a.lang)
    store.setdefault("entries", {})
    n = 0
    p = work / f"{a.lang}.drafts.jsonl"
    for line in p.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        e = store["entries"].get(d["k"])
        if e and (e.get("reviewed") or e.get("source") != "llm"):
            continue
        store["entries"][d["k"]] = {"romanization": d["r"], "scheme": f"{a.lang}-learner-v1", "source": "llm", "reviewed": False}
        n += 1
    save_store(a.lang, store)
    print(f"merged {n} into {a.lang}.json (total {len(store['entries'])})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--lang", required=True)
    r.add_argument("--work", required=True)
    r.add_argument("--batch", type=int, default=120)
    r.add_argument("--jobs", type=int, default=6)
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--model", default=None)
    r.add_argument("--max-fails", type=int, default=8)
    m = sub.add_parser("merge")
    m.add_argument("--lang", required=True)
    m.add_argument("--work", required=True)
    a = ap.parse_args()
    {"run": cmd_run, "merge": cmd_merge}[a.cmd](a)
