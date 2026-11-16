import { describe, expect, it } from "vitest";
import { isBetaCourse, isBetaLanguage } from "./beta";
import { KEYBOARD_LAYOUTS } from "@lingo/shared/lib/scripts";

describe("beta labelling", () => {
  it("flags fa and prs only", () => {
    expect(isBetaLanguage("fa")).toBe(true);
    expect(isBetaLanguage("prs")).toBe(true);
    expect(isBetaLanguage("nl")).toBe(false);
    expect(isBetaCourse({ source_language: "en", target_language: "prs" })).toBe(true);
    expect(isBetaCourse({ source_language: "fa", target_language: "en" })).toBe(true);
    expect(isBetaCourse({ source_language: "en", target_language: "nl" })).toBe(false);
  });
});

describe("fa/prs keyboard punctuation", () => {
  it("offers . ! ، ؟ on the symbol layer", () => {
    const keys = KEYBOARD_LAYOUTS.arabic?.symbols?.keys ?? [];
    for (const k of [".", "!", "،", "؟"]) expect(keys).toContain(k);
  });
});
