import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  RELOAD_FLAG,
  installStaleChunkReload,
  isChunkLoadError,
  reloadOnceForStaleChunk,
} from "./staleChunkReload";

beforeEach(() => sessionStorage.clear());

describe("isChunkLoadError", () => {
  it("matches dynamic import failures", () => {
    expect(isChunkLoadError(new TypeError("Failed to fetch dynamically imported module: /a.js"))).toBe(true);
    expect(isChunkLoadError("error loading dynamically imported module")).toBe(true);
    expect(isChunkLoadError(new Error("boom"))).toBe(false);
    expect(isChunkLoadError(null)).toBe(false);
  });
});

describe("reloadOnceForStaleChunk", () => {
  it("reloads once then refuses", () => {
    const reload = vi.fn();
    expect(reloadOnceForStaleChunk(reload)).toBe(true);
    expect(reloadOnceForStaleChunk(reload)).toBe(false);
    expect(reload).toHaveBeenCalledTimes(1);
    expect(sessionStorage.getItem(RELOAD_FLAG)).toBe("1");
  });
  it("does not reload when storage throws", () => {
    const reload = vi.fn();
    const bad = { getItem: () => { throw new Error("x"); }, setItem: vi.fn() };
    expect(reloadOnceForStaleChunk(reload, bad)).toBe(false);
    expect(reload).not.toHaveBeenCalled();
  });
});

describe("installStaleChunkReload", () => {
  it("handles vite:preloadError by preventing default and setting the flag", () => {
    installStaleChunkReload();
    const reload = vi.fn();
    Object.defineProperty(window, "location", {
      value: { ...window.location, reload },
      configurable: true,
    });
    const ev = new Event("vite:preloadError", { cancelable: true });
    window.dispatchEvent(ev);
    expect(ev.defaultPrevented).toBe(true);
    expect(reload).toHaveBeenCalledTimes(1);
    const ev2 = new Event("vite:preloadError", { cancelable: true });
    window.dispatchEvent(ev2);
    expect(ev2.defaultPrevented).toBe(false);
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
