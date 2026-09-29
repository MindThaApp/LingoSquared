import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AudioUrlCache, audioCacheKey } from "./audioCache";

describe("AudioUrlCache", () => {
  let revoke: ReturnType<typeof vi.fn>;
  beforeEach(() => {
    revoke = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, { revokeObjectURL: revoke }));
  });
  afterEach(() => vi.unstubAllGlobals());

  it("hit returns the same URL; key includes text, lang and rate", () => {
    const c = new AudioUrlCache(3);
    const k = audioCacheKey("hoi", "nl", 1);
    c.set(k, "blob:1");
    expect(c.get(k)).toBe("blob:1");
    expect(c.get(audioCacheKey("hoi", "nl", 1.25))).toBeUndefined();
    expect(c.get(audioCacheKey("hoi", "de", 1))).toBeUndefined();
    expect(revoke).not.toHaveBeenCalled();
  });

  it("evicts the oldest at cap and revokes its URL only", () => {
    const c = new AudioUrlCache(2);
    c.set("a", "blob:a");
    c.set("b", "blob:b");
    c.set("c", "blob:c");
    expect(revoke).toHaveBeenCalledTimes(1);
    expect(revoke).toHaveBeenCalledWith("blob:a");
    expect(c.get("a")).toBeUndefined();
    expect(c.size).toBe(2);
  });

  it("get updates recency so the touched entry survives eviction", () => {
    const c = new AudioUrlCache(2);
    c.set("a", "blob:a");
    c.set("b", "blob:b");
    c.get("a");
    c.set("c", "blob:c");
    expect(revoke).toHaveBeenCalledWith("blob:b");
    expect(c.get("a")).toBe("blob:a");
  });
});
