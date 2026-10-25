import { describe, expect, it } from "vitest";
import en from "../../../packages/shared/src/i18n/locales/en.json";
import nl from "../../../packages/shared/src/i18n/locales/nl.json";
import fa from "../../../packages/shared/src/i18n/locales/fa.json";
import prs from "../../../packages/shared/src/i18n/locales/prs.json";

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

const enKeys = new Set(flatten(en as Tree).map(base));

describe.each([
  ["nl", nl],
  ["fa", fa],
  ["prs", prs],
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
});
