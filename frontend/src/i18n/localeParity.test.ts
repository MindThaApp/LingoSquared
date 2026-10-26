import { describe, expect, it } from "vitest";
import en from "../../../packages/shared/src/i18n/locales/en.json";
import nl from "../../../packages/shared/src/i18n/locales/nl.json";
import fa from "../../../packages/shared/src/i18n/locales/fa.json";
import prs from "../../../packages/shared/src/i18n/locales/prs.json";
import esLocale from "../../../packages/shared/src/i18n/locales/es.json";
import frLocale from "../../../packages/shared/src/i18n/locales/fr.json";
import ruLocale from "../../../packages/shared/src/i18n/locales/ru.json";
import itLocale from "../../../packages/shared/src/i18n/locales/it.json";
import arLocale from "../../../packages/shared/src/i18n/locales/ar.json";
import plLocale from "../../../packages/shared/src/i18n/locales/pl.json";
import hiLocale from "../../../packages/shared/src/i18n/locales/hi.json";
import roLocale from "../../../packages/shared/src/i18n/locales/ro.json";
import koLocale from "../../../packages/shared/src/i18n/locales/ko.json";
import zhLocale from "../../../packages/shared/src/i18n/locales/zh.json";
import jaLocale from "../../../packages/shared/src/i18n/locales/ja.json";

type Tree = { [k: string]: string | Tree };

function flatten(tree: Tree, prefix = ""): string[] {
  return Object.entries(tree).flatMap(([k, v]) =>
    typeof v === "string" ? [prefix + k] : flatten(v, `${prefix}${k}.`),
  );
}

// i18next plural forms (key_one, key_other, ...) are language-specific, so a
// locale may legitimately carry them instead of the bare en key. Compare on
// the plural-stripped base key.
const PLURAL = /_(zero|one|two|few|many|other)$/;
const base = (key: string) => key.replace(PLURAL, "");

function flatten2(tree: Tree, prefix = "", out: Record<string, string> = {}) {
  for (const [k, v] of Object.entries(tree)) {
    if (typeof v === "string") out[prefix + k] = v;
    else flatten2(v, `${prefix}${k}.`, out);
  }
  return out;
}
const enFlat = flatten2(en as Tree);
const enPluralBases = Object.keys(enFlat)
  .filter((k) => k.endsWith("_one") && `${k.slice(0, -4)}_other` in enFlat)
  .map((k) => k.slice(0, -4));
const placeholders = (s: string) => (s.match(/\{\{[^}]+\}\}/g) ?? []).sort().join("|");

const enKeys = new Set(flatten(en as Tree).map(base));

describe.each([
  ["nl", nl],
  ["fa", fa],
  ["prs", prs],
  ["es", esLocale],
  ["fr", frLocale],
  ["ru", ruLocale],
  ["it", itLocale],
  ["ar", arLocale],
  ["pl", plLocale],
  ["hi", hiLocale],
  ["ro", roLocale],
  ["ko", koLocale],
  ["zh", zhLocale],
  ["ja", jaLocale],
])("locale %s", (_name, locale) => {
  const keys = new Set(flatten(locale as Tree).map(base));

  it("has every key that en has", () => {
    const missing = [...enKeys].filter((k) => !keys.has(k));
    expect(missing).toEqual([]);
  });

  it("has no keys that en lacks", () => {
    const extra = [...keys].filter((k) => !enKeys.has(k));
    expect(extra).toEqual([]);
  });

  const flat = flatten2(locale as Tree);

  it("keeps placeholders identical to en", () => {
    const bad: string[] = [];
    for (const [k, v] of Object.entries(enFlat)) {
      if (!(k in flat)) continue; // plural-split or missing keys are covered elsewhere
      if (placeholders(v) !== placeholders(flat[k])) bad.push(k);
    }
    expect(bad).toEqual([]);
  });

  it("has exactly the CLDR plural categories for its language", () => {
    const cats = [...new Intl.PluralRules(_name as string).resolvedOptions().pluralCategories].sort();
    const bad: string[] = [];
    for (const b of enPluralBases) {
      const have = cats.filter((c) => `${b}_${c}` in flat);
      const extra = ["zero", "one", "two", "few", "many", "other"].filter(
        (c) => !cats.includes(c as never) && `${b}_${c}` in flat,
      );
      if (have.length !== cats.length || extra.length) bad.push(b);
      for (const c of cats) {
        const v = flat[`${b}_${c}`];
        if (v !== undefined && !["zero", "one", "two"].includes(c) && !v.includes("{{count}}")) bad.push(`${b}_${c} lacks {{count}}`);
      }
    }
    expect(bad).toEqual([]);
  });
});
