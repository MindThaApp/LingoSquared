import { describe, expect, it } from "vitest";
import { answerWhy } from "./answerWhy";

const base = { text_blocks: [] };

describe("answerWhy", () => {
  it("is empty when the content carries no explanation", () => {
    expect(answerWhy({ ...base })).toEqual([]);
    expect(answerWhy(undefined)).toEqual([]);
    expect(answerWhy({ ...base, note: "   " })).toEqual([]);
  });

  it("returns authored explanation, grammar note and gloss only", () => {
    expect(
      answerWhy({ ...base, explanation: "Because.", grammar_note: "Copula.", gloss: "I am", other: "x" }),
    ).toEqual(["Because.", "Copula.", "I am"]);
  });

  it("de-duplicates identical text", () => {
    expect(answerWhy({ ...base, note: "Same", gloss: "Same" })).toEqual(["Same"]);
  });
});
