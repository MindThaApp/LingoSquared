import { describe, expect, it } from "vitest";
import { seededShuffle, seededShuffleNotOriginal } from "./shuffle";

describe("seededShuffle", () => {
  it("is deterministic per seed and a permutation", () => {
    const items = ["a", "b", "c", "d", "e", "f"];
    expect(seededShuffle(items, "s1")).toEqual(seededShuffle(items, "s1"));
    expect(seededShuffle(items, "s1").slice().sort()).toEqual(items);
    const orders = new Set(Array.from({ length: 30 }, (_, i) => seededShuffle(items, `x${i}`).join("")));
    expect(orders.size).toBeGreaterThan(5);
  });
  it("does not mutate input", () => {
    const items = ["a", "b", "c"];
    seededShuffle(items, "z");
    expect(items).toEqual(["a", "b", "c"]);
  });
  it("NotOriginal never returns the original order for 3 tiles", () => {
    const items = ["Ben", "jij", "nieuw"];
    for (let i = 0; i < 500; i++) {
      expect(seededShuffleNotOriginal(items, `seed${i}`)).not.toEqual(items);
    }
  });
  it("handles duplicates and single-distinct banks", () => {
    expect(seededShuffleNotOriginal(["a", "a"], "s")).toEqual(["a", "a"]);
    for (let i = 0; i < 100; i++) {
      expect(seededShuffleNotOriginal(["a", "a", "b"], `s${i}`)).not.toEqual(["a", "a", "b"]);
    }
  });
});
