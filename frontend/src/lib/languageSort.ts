import type { TFunction } from "i18next";
import { localizedLanguageName } from "@lingo/shared/lib/localizedLanguageName";
import type { Language } from "@lingo/shared/api/types";

/** Sort languages by their display name in the UI language (localeCompare with the UI locale). */
export function sortLanguagesByLocalizedName(
  languages: Language[],
  t: TFunction,
  uiLocale: string,
): Language[] {
  const name = (l: Language) => localizedLanguageName(l.code, t, l.name) ?? l.name ?? l.code;
  let compare: (a: string, b: string) => number;
  try {
    const collator = new Intl.Collator(uiLocale || undefined);
    compare = (a, b) => collator.compare(a, b);
  } catch {
    compare = (a, b) => a.localeCompare(b);
  }
  return [...languages].sort((a, b) => compare(name(a), name(b)) || a.code.localeCompare(b.code));
}

/** Target languages that have at least one real course for `source`, sorted by localized name. */
export function pickerTargetLanguages(
  languages: Language[],
  source: string,
  byPair: Map<string, number>,
  t: TFunction,
  uiLocale: string,
): Language[] {
  return sortLanguagesByLocalizedName(
    languages.filter((l) => l.code !== source && (byPair.get(`${source}:${l.code}`) ?? 0) > 0),
    t,
    uiLocale,
  );
}
