import { describe, expect, it } from "vitest";
import type { Exercise } from "@lingo/shared/api/types";
import { buildWordBank, tokenize } from "./wordBankTiles";

function ex(id: string, text: string, lang: string, extra: Partial<Exercise["prompt"]> = {}): Exercise {
  return {
    id,
    type: "translation",
    order: 1,
    prompt: { text_blocks: [{ text, language_code: lang, direction: "ltr" }], answer_language_code: "nl", ...extra },
  };
}

const lesson: Exercise[] = [
  ex("a", "I am tired", "en"),
  ex("b", "Ik ben moe.", "nl"),
  ex("c", "Wij hebben honger, dorst!", "nl"),
  ex("d", "x", "en", { options: ["koffie", "thee", "melk"] }),
  ex("e", "y", "en", { word_bank: ["brood", "kaas"], answer_language_code: "nl" }),
  ex("f", "z", "en", { options: ["bread"], answer_language_code: "en" }),
];

describe("tokenize", () => {
  it("strips edge punctuation (incl. Arabic and guillemets), keeps case and inner apostrophes", () => {
    expect(tokenize("«Hallo,» Wereld! zo'n")).toEqual(["Hallo", "Wereld", "zo'n"]);
    expect(tokenize("سلام، چطوری؟ ؛")).toEqual(["سلام", "چطوری"]);
    expect(tokenize("  ...  ")).toEqual([]);
  });
});

describe("buildWordBank", () => {
  it("answerHint path: exactly answer tokens + 2-4 distractors not in the answer", () => {
    const cur = ex("cur", "I am hungry", "en");
    const { tiles, source } = buildWordBank({
      exercise: cur,
      lessonExercises: [...lesson, cur],
      answerHint: "Ik heb honger",
      targetLanguage: "nl",
    });
    expect(source).toBe("answer");
    const answer = ["Ik", "heb", "honger"];
    const rest = [...tiles];
    for (const a of answer) rest.splice(rest.indexOf(a), 1);
    expect(rest.length).toBeGreaterThanOrEqual(2);
    expect(rest.length).toBeLessThanOrEqual(4);
    expect(new Set(rest.map((t) => t.toLowerCase())).size).toBe(rest.length);
    for (const d of rest) expect(answer.map((a) => a.toLowerCase())).not.toContain(d.toLowerCase());
  });

  it("answerHint path keeps duplicate answer tokens with multiplicity", () => {
    const cur = ex("cur", "q", "en");
    const { tiles } = buildWordBank({ exercise: cur, lessonExercises: lesson, answerHint: "de man de vrouw", targetLanguage: "nl" });
    expect(tiles.filter((t) => t === "de")).toHaveLength(2);
  });

  it("prompt.word_bank is used as-is (no strip, dedupe or distractors), shuffled by index-stable content", () => {
    const wb = ["Ik", "heb", "een", "een.", "Ik"];
    const cur = ex("cur", "q", "en", { word_bank: wb });
    const { tiles, source } = buildWordBank({ exercise: cur, lessonExercises: lesson, answerHint: "x y z", targetLanguage: "nl" });
    expect(source).toBe("prompt"); // precedence over answerHint
    expect([...tiles].sort()).toEqual([...wb].sort());
  });

  it("punctuation is stripped only on the answerHint path", () => {
    const cur = ex("cur", "q", "en");
    const hint = buildWordBank({ exercise: cur, lessonExercises: [cur], answerHint: "Hallo, wereld!", targetLanguage: "nl" });
    expect(hint.tiles).toEqual(expect.arrayContaining(["Hallo", "wereld"]));
    expect(hint.tiles.some((t) => /[,!]/.test(t))).toBe(false);
    const prompt = buildWordBank({ exercise: ex("c2", "q", "en", { word_bank: ["Hallo,", "wereld!"] }), targetLanguage: "nl" });
    expect(prompt.tiles.sort()).toEqual(["Hallo,", "wereld!"]);
  });

  it("no word_bank and no answerHint -> no bank", () => {
    const cur = ex("cur", "I am hungry", "en");
    expect(buildWordBank({ exercise: cur, lessonExercises: [...lesson, cur], targetLanguage: "nl" }).tiles).toEqual([]);
  });

  it("a word_bank with fewer than 2 entries is ignored", () => {
    const cur = ex("cur", "q", "en", { word_bank: ["een"] });
    expect(buildWordBank({ exercise: cur, targetLanguage: "nl" }).tiles).toEqual([]);
  });
});
