import { afterEach, describe, expect, it, vi } from "vitest";
import {
  defaultShowTranslit,
  getTranslitPreference,
  resolveShowTranslit,
  setTranslitPreference,
  translitAvailableFor,
} from "./translitPreference";

afterEach(() => {
  localStorage.clear();
  vi.unstubAllEnvs();
});

describe("translitPreference", () => {
  it("defaults on at A1 and off from A2", () => {
    expect(defaultShowTranslit("A1")).toBe(true);
    expect(defaultShowTranslit("A2")).toBe(false);
    expect(defaultShowTranslit("B1")).toBe(false);
    expect(defaultShowTranslit(null)).toBe(false);
  });

  it("stored choice wins over the level default, per user", () => {
    expect(resolveShowTranslit("u1", "A1")).toBe(true);
    setTranslitPreference("u1", false);
    expect(resolveShowTranslit("u1", "A1")).toBe(false);
    expect(resolveShowTranslit("u2", "A1")).toBe(true);
    setTranslitPreference("u2", true);
    expect(resolveShowTranslit("u2", "B2")).toBe(true);
    expect(getTranslitPreference(null)).toBeNull();
  });

  it("never throws when storage is unavailable", () => {
    const spy = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(getTranslitPreference("u1")).toBeNull();
    spy.mockRestore();
  });

  it("covers ru/hi always and ar/fa/prs only while unreviewed drafts are enabled", () => {
    expect(translitAvailableFor("ru")).toBe(true);
    expect(translitAvailableFor("hi")).toBe(true);
    expect(translitAvailableFor("fa")).toBe(true);
    expect(translitAvailableFor("nl")).toBe(false);
    vi.stubEnv("VITE_TRANSLIT_SHOW_UNREVIEWED", "false");
    expect(translitAvailableFor("fa")).toBe(false);
    expect(translitAvailableFor("prs")).toBe(false);
    expect(translitAvailableFor("ar")).toBe(false);
    expect(translitAvailableFor("ru")).toBe(true);
  });
});
