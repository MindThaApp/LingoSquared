import { describe, expect, it } from "vitest";
import type { TFunction } from "i18next";
import type { Language } from "@lingo/shared/api/types";
import { pickerTargetLanguages, sortLanguagesByLocalizedName } from "./languageSort";

const names: Record<string, string> = {
  "language_names.de": "Duits",
  "language_names.fr": "Frans",
  "language_names.es": "Spaans",
  "language_names.en": "Engels",
};
const t = ((key: string) => names[key] ?? key) as unknown as TFunction;
const lang = (code: string): Language =>
  ({ code, name: code.toUpperCase(), native_name: code, direction: "ltr" }) as Language;

describe("language picker ordering", () => {
  it("sorts by localized name, not ISO code", () => {
    const sorted = sortLanguagesByLocalizedName([lang("es"), lang("de"), lang("fr")], t, "nl");
    expect(sorted.map((l) => l.code)).toEqual(["de", "fr", "es"]); // Duits, Frans, Spaans
  });

  it("lists only targets that have a course for the source", () => {
    const byPair = new Map([
      ["en:fr", 30],
      ["en:de", 25],
      ["fr:es", 40],
    ]);
    const targets = pickerTargetLanguages(
      [lang("en"), lang("es"), lang("de"), lang("fr")],
      "en",
      byPair,
      t,
      "nl",
    );
    expect(targets.map((l) => l.code)).toEqual(["de", "fr"]);
  });
});
