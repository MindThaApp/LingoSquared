import { describe, expect, it } from "vitest";
import type { ReviewItem } from "@lingo/shared/api/types";
import { filterDueReviews, shouldShowFixCard, tallyFixResults } from "./fixMistakes";

const NOW = new Date("2026-07-15T12:00:00.000Z");

function item(id: string, due_at: string): ReviewItem {
  return {
    id,
    exercise_id: `ex-${id}`,
    due_at,
    mastery: 0,
    exercise: { id: `ex-${id}`, type: "translation", prompt: {} as ReviewItem["exercise"]["prompt"] },
  };
}

describe("filterDueReviews", () => {
  it("includes past-due and exactly-now items, excludes future ones", () => {
    const items = [
      item("past", "2026-07-14T00:00:00.000Z"),
      item("now", "2026-07-15T12:00:00.000Z"),
      item("future", "2026-07-16T00:00:00.000Z"),
    ];
    expect(filterDueReviews(items, NOW).map((i) => i.id)).toEqual(["past", "now"]);
  });
  it("excludes items with an invalid date", () => {
    expect(filterDueReviews([item("bad", "not-a-date")], NOW)).toEqual([]);
  });
  it("returns an empty list for empty input", () => {
    expect(filterDueReviews([], NOW)).toEqual([]);
  });
});

describe("shouldShowFixCard", () => {
  it("hides on empty and shows for a mixed list's due count", () => {
    expect(shouldShowFixCard(filterDueReviews([], NOW).length)).toBe(false);
    const mixed = [item("a", "2026-07-01T00:00:00Z"), item("b", "2027-01-01T00:00:00Z"), item("c", "x")];
    const n = filterDueReviews(mixed, NOW).length;
    expect(n).toBe(1);
    expect(shouldShowFixCard(n)).toBe(true);
  });
});

describe("tallyFixResults", () => {
  it("counts fixed vs total", () => {
    expect(tallyFixResults([true, false, true])).toEqual({ total: 3, fixed: 2 });
    expect(tallyFixResults([])).toEqual({ total: 0, fixed: 0 });
  });
});
