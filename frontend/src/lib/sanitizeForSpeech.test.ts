import { describe, expect, it } from "vitest";
import { sanitizeForSpeech } from "./sanitizeForSpeech";

describe("sanitizeForSpeech", () => {
  it("strips a leading speaker label", () => {
    expect(sanitizeForSpeech("Lotte: Hoi, hoe gaat het?")).toBe("Hoi, hoe gaat het?");
    expect(sanitizeForSpeech("Jan de Vries: Goedemorgen")).toBe("Goedemorgen");
  });
  it("strips non-Latin speaker labels", () => {
    expect(sanitizeForSpeech("علی: سلام")).toBe("سلام");
    expect(sanitizeForSpeech("Иван: Привет")).toBe("Привет");
    expect(sanitizeForSpeech("李明：你好")).toBe("你好");
  });
  it("strips parenthesized and bracketed glosses", () => {
    expect(sanitizeForSpeech("Hoi (stressed informal) allemaal")).toBe("Hoi allemaal");
    expect(sanitizeForSpeech("Goedemorgen [lit. good morning]")).toBe("Goedemorgen");
  });
  it("replaces arrows and collapses whitespace", () => {
    expect(sanitizeForSpeech("huis → house")).toBe("huis, house");
    expect(sanitizeForSpeech("a -> b => c")).toBe("a, b, c");
    expect(sanitizeForSpeech("  veel   spaties  ")).toBe("veel spaties");
  });
  it("does not strip times or mid-sentence colons", () => {
    expect(sanitizeForSpeech("10:30 komt de trein")).toBe("10:30 komt de trein");
    expect(sanitizeForSpeech("Ik zei het volgende: ja")).toBe("Ik zei het volgende: ja");
    expect(sanitizeForSpeech("Om 10:30 begint het: kom")).toBe("Om 10:30 begint het: kom");
  });
  it("returns empty string when nothing speakable remains", () => {
    expect(sanitizeForSpeech("(only a gloss)")).toBe("");
    expect(sanitizeForSpeech("   ")).toBe("");
  });
});
