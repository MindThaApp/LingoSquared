import { describe, expect, it } from "vitest";
import { detectUiLanguage, mapLocaleTag } from "./detectLocale";

describe("detectUiLanguage", () => {
  it("maps fa-AF to prs and fa-IR to fa", () => {
    expect(mapLocaleTag("fa-AF")).toBe("prs");
    expect(mapLocaleTag("fa")).toBe("fa");
    expect(mapLocaleTag("fa-IR")).toBe("fa");
  });
  it("maps regional and script variants to the base language", () => {
    expect(detectUiLanguage(["nl-BE"])).toBe("nl");
    expect(detectUiLanguage(["zh-Hans-CN"])).toBe("zh");
    expect(detectUiLanguage(["pt-BR", "de-DE", "fr-CA"])).toBe("fr");
  });
  it("falls back to en", () => {
    expect(detectUiLanguage(["sw", "de"])).toBe("en");
    expect(detectUiLanguage([])).toBe("en");
    expect(detectUiLanguage(undefined)).toBe("en");
  });
});
