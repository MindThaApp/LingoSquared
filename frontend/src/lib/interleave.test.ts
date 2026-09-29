import { describe, expect, it } from "vitest";
import type { Exercise, TeachingCard } from "@lingo/shared/api/types";
import {
  buildLessonBlocks,
  chunkSizes,
  contentTokens,
  flattenBlocks,
  matchExercisesToCards,
} from "./interleave";

function card(headword: string, gloss: string): TeachingCard {
  return {
    kind: "vocabulary",
    title: gloss,
    text_blocks: [
      { text: headword, language_code: "nl", direction: "ltr" },
      { text: gloss, language_code: "en", direction: "ltr" },
    ],
  };
}

function ex(n: number, prompt: Record<string, unknown>, instruction = "Choose the right answer."): Exercise {
  return {
    id: `e${n}`,
    type: "multiple_choice",
    order: n,
    prompt: {
      text_blocks: [{ text: instruction, language_code: "en", direction: "ltr" }],
      ...prompt,
    },
  };
}

const WORDS = ["appel", "banaan", "kaas", "melk", "brood", "water", "koffie", "thee"];
const cards = WORDS.map((w, i) => card(w, `gloss${i}word`));

// One exercise per card, deliberately authored in REVERSE card order for the
// first two so within-block authored order is observable.
function typicalExercises(): Exercise[] {
  return [
    ex(1, { options: ["appel", "x1", "x2"] }),
    ex(2, { audio_text: "banaan" }),
    ex(3, { word_bank: ["kaas", "qqq"] }),
    ex(4, { pairs: [{ left: "brood", right: "bread" }] }),
    ex(5, { text_blocks: [{ text: "Vertaal water", language_code: "nl", direction: "ltr" }] }),
    ex(6, { options: ["koffie"] }),
    ex(7, { options: ["thee"] }),
  ];
}

describe("normalization", () => {
  it("lowercases, strips punctuation and drops short/stop words", () => {
    expect(contentTokens("The Appel, de kaas!")).toEqual(["appel", "kaas"]);
  });
  it("handles Persian, Cyrillic and CJK", () => {
    expect(contentTokens("سلام، چطوری؟")).toEqual(["سلام", "چطوری"]);
    expect(contentTokens("Привет, мир, и")).toEqual(["привет", "мир"]);
    expect(contentTokens("你好")).toEqual(["你好"]);
  });
  it("NFC-normalizes decomposed text", () => {
    expect(contentTokens("café")).toEqual(contentTokens("café"));
  });
});

describe("chunkSizes", () => {
  it("groups of at most 3, no lone card unless n=1", () => {
    expect(chunkSizes(1)).toEqual([1]);
    expect(chunkSizes(4)).toEqual([2, 2]);
    expect(chunkSizes(7)).toEqual([3, 2, 2]);
    expect(chunkSizes(10)).toEqual([3, 3, 2, 2]);
  });
});

describe("buildLessonBlocks", () => {
  it("matched mode: exercise lands in the block of its latest matched card, in authored order", () => {
    const { blocks, mode } = buildLessonBlocks(cards, typicalExercises());
    expect(mode).toBe("matched");
    // 8 cards -> 3,3,2. e1..e3 -> block 0, e4..e5 (brood, water) + fills -> block 1, e6,e7 -> block 2
    expect(blocks.map((b) => b.cards.length)).toEqual([3, 3, 2]);
    expect(blocks[0].exercises.map((e) => e.id)).toEqual(["e1", "e2", "e3"]);
    expect(blocks[1].exercises.map((e) => e.id)).toEqual(["e4", "e5"]);
    expect(blocks[2].exercises.map((e) => e.id)).toEqual(["e6", "e7"]);
  });

  it("an exercise mentioning several cards waits for the latest one", () => {
    const exs = [ex(1, { options: ["appel", "thee"] }), ...typicalExercises().slice(1)];
    const { blocks } = buildLessonBlocks(cards, exs);
    const home = blocks.findIndex((b) => b.exercises.some((e) => e.id === "e1"));
    expect(home).toBe(2);
  });

  it("never shows more than 3 cards before an exercise and keeps everything exactly once", () => {
    const manyCards = Array.from({ length: 10 }, (_, i) => card(`woord${i}`, `meaning${i}x`));
    // Everything matches only the LAST card -> earlier blocks would be empty.
    const exs = Array.from({ length: 8 }, (_, i) => ex(i + 1, { audio_text: "woord9" }));
    const { blocks, mode } = buildLessonBlocks(manyCards, exs);
    expect(mode).toBe("matched");
    let run = 0;
    for (const b of blocks) {
      run = b.cards.length;
      expect(run).toBeLessThanOrEqual(3);
      expect(b.exercises.length).toBeGreaterThan(0);
    }
    expect(blocks.flatMap((b) => b.cards)).toEqual(manyCards);
    expect(blocks.flatMap((b) => b.exercises).map((e) => e.id).sort()).toEqual(exs.map((e) => e.id).sort());
    // No cards trail the last exercise.
    expect(blocks[blocks.length - 1].exercises.length).toBeGreaterThan(0);
  });

  it("unmatched exercises keep relative order after the last block's own exercises", () => {
    const exs = [...typicalExercises(), ex(8, { audio_text: "zzzzz" }), ex(9, { audio_text: "yyyyy" })];
    const { blocks } = buildLessonBlocks(cards, exs);
    const last = blocks[blocks.length - 1].exercises.map((e) => e.id);
    expect(last.slice(-2)).toEqual(["e8", "e9"]);
  });

  it("falls back to rhythm (2 cards, 2 exercises) when fewer than half of exercises match", () => {
    const exs = Array.from({ length: 8 }, (_, i) => ex(i + 1, { audio_text: `onbekend${i}` }));
    const { blocks, mode } = buildLessonBlocks(cards, exs);
    expect(mode).toBe("rhythm");
    expect(blocks.map((b) => [b.cards.length, b.exercises.length])).toEqual([
      [2, 2],
      [2, 2],
      [2, 2],
      [2, 2],
    ]);
    expect(blocks.flatMap((b) => b.exercises).map((e) => e.id)).toEqual(exs.map((e) => e.id));
    expect(blocks.flatMap((b) => b.cards)).toEqual(cards);
  });

  it("rhythm never leaves cards after the last exercise", () => {
    const manyCards = Array.from({ length: 10 }, (_, i) => card(`woord${i}`, `meaning${i}x`));
    const exs = Array.from({ length: 4 }, (_, i) => ex(i + 1, { audio_text: `onbekend${i}` }));
    const { blocks, mode } = buildLessonBlocks(manyCards, exs);
    expect(mode).toBe("rhythm");
    expect(blocks.every((b) => b.exercises.length > 0)).toBe(true);
    expect(blocks.flatMap((b) => b.cards)).toEqual(manyCards);
  });

  it("all cards, no exercises -> a single cards-only block", () => {
    const { blocks } = buildLessonBlocks(cards, []);
    expect(blocks).toEqual([{ cards, exercises: [] }]);
  });

  it("all exercises, no cards -> a single exercises-only block", () => {
    const exs = typicalExercises();
    const { blocks } = buildLessonBlocks([], exs);
    expect(blocks).toEqual([{ cards: [], exercises: exs }]);
  });

  it("both empty -> no blocks", () => {
    expect(buildLessonBlocks([], []).blocks).toEqual([]);
  });

  it("English glosses like 'the'/'a' do not create matches", () => {
    const c = [card("de", "the"), card("een", "a")];
    const e = [ex(1, { audio_text: "the a" })];
    expect(matchExercisesToCards(c, e)).toEqual([-1]);
  });
});

describe("flattenBlocks", () => {
  it("reports cumulative cardsBefore per exercise", () => {
    const { blocks } = buildLessonBlocks(cards, typicalExercises());
    const flat = flattenBlocks(blocks);
    expect(flat.map((f) => f.cardsBefore)).toEqual([3, 3, 3, 6, 6, 8, 8]);
    expect(flat.map((f) => f.exercise.id)).toEqual(["e1", "e2", "e3", "e4", "e5", "e6", "e7"]);
  });
});
