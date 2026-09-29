import { describe, expect, it } from "vitest";
import { diffAnswers } from "./answerDiff";

const changed = (segs: { text: string; changed: boolean }[]) =>
  segs.filter((s) => s.changed).map((s) => s.text);
const join = (segs: { text: string }[]) => segs.map((s) => s.text).join("");

describe("diffAnswers", () => {
  it("diffs Latin single words per character (hous vs huis)", () => {
    const d = diffAnswers("hous", "huis");
    expect(d.mode).toBe("char");
    expect(join(d.learner)).toBe("hous");
    expect(join(d.correct)).toBe("huis");
    expect(changed(d.learner)).toEqual(["o"]);
    expect(changed(d.correct)).toEqual(["i"]);
  });

  it("diffs Persian per character (کتب vs کتاب)", () => {
    const d = diffAnswers("کتب", "کتاب");
    expect(d.mode).toBe("char");
    expect(changed(d.learner)).toEqual([]);
    expect(changed(d.correct)).toEqual(["ا"]);
    expect(join(d.correct)).toBe("کتاب");
  });

  it("diffs sentences per word", () => {
    const d = diffAnswers("ik heb een hond", "ik heb een kat");
    expect(d.mode).toBe("word");
    expect(changed(d.learner)).toEqual(["hond"]);
    expect(changed(d.correct)).toEqual(["kat"]);
    expect(join(d.correct)).toBe("ik heb een kat");
  });

  it("does not split surrogate pairs", () => {
    const d = diffAnswers("a😀", "a😀b");
    expect(changed(d.correct)).toEqual(["b"]);
    expect(changed(d.learner)).toEqual([]);
  });

  it("marks an identical answer as fully unchanged", () => {
    const d = diffAnswers("huis", "huis");
    expect(changed(d.learner)).toEqual([]);
    expect(changed(d.correct)).toEqual([]);
  });
});
