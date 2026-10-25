import { describe, expect, it } from "vitest";
import { audioKey, normalizeAudioText, prerenderedAudioFile, sha256Hex } from "@lingo/shared/audio/audioKey";

// The same vectors are asserted by backend/tests/test_audio_prerender.py:
// they pin the TS and Python implementations to each other.
describe("audioKey", () => {
  it("sha256 matches known vectors", () => {
    expect(sha256Hex("")).toBe("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    expect(sha256Hex("abc")).toBe("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    // multi-block, non-ASCII input
    expect(sha256Hex("x".repeat(200) + "é")).toHaveLength(64);
  });

  it("matches the Python implementation", () => {
    expect(audioKey("google", "en-US-Neural2-C", "en", "Hello  world", "1.00")).toBe("18ab77b27d268b236c607e04aca81acb");
  });

  it("normalizes NFC and whitespace", () => {
    expect(normalizeAudioText("  é   x\n")).toBe("é x");
  });

  it("maps a language to a file and ignores unknown languages / empty text", () => {
    expect(prerenderedAudioFile("hallo", "nl")).toMatch(/^[0-9a-f]{32}\.mp3$/);
    expect(prerenderedAudioFile("hallo", "nl-NL")).toBe(prerenderedAudioFile("hallo", "nl"));
    expect(prerenderedAudioFile("   ", "nl")).toBeNull();
    expect(prerenderedAudioFile("hallo", "zz")).toBeNull();
  });

  it("is deterministic and voice-sensitive", () => {
    const a = audioKey("google", "v1", "nl", "hallo", "1.00");
    expect(audioKey("google", "v1", "nl", "hallo", "1.00")).toBe(a);
    expect(audioKey("google", "v2", "nl", "hallo", "1.00")).not.toBe(a);
  });
});
