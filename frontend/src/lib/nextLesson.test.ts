import { describe, expect, it } from "vitest";
import type { LessonSummary, UnitSummary } from "@lingo/shared/api/types";
import { computeNextItem } from "./nextLesson";

const unit = (id: string, order: number, over: Partial<UnitSummary> = {}): UnitSummary => ({
  id, title: id, order, lesson_count: 2, completed_lesson_count: 0,
  section: "reading_writing", locked: false, checkpoint_passed: false, content_key: null, ...over,
});
const lesson = (id: string, order: number): LessonSummary => ({ id, title: id, order, exercise_count: 5 });

const units = [unit("u1", 1), unit("u2", 2)];
const l1 = [lesson("b", 2), lesson("a", 1)];

describe("computeNextItem", () => {
  it("mid-unit goes to the next lesson by order", () => {
    expect(computeNextItem(units, "u1", l1, undefined, "a")).toEqual({ kind: "lesson", lessonId: "b", unitId: "u1" });
  });
  it("last lesson goes to next unit's first lesson", () => {
    expect(computeNextItem(units, "u1", l1, [lesson("d", 2), lesson("c", 1)], "b")).toEqual({
      kind: "lesson", lessonId: "c", unitId: "u2",
    });
  });
  it("next unit with no lessons goes to its checkpoint", () => {
    expect(computeNextItem(units, "u1", l1, [], "b")).toEqual({ kind: "checkpoint", unitId: "u2" });
  });
  it("last unit returns null", () => {
    expect(computeNextItem(units, "u2", l1, undefined, "b")).toBeNull();
  });
  it("locked next unit returns null", () => {
    expect(computeNextItem([unit("u1", 1), unit("u2", 2, { locked: true })], "u1", l1, [lesson("c", 1)], "b")).toBeNull();
  });
  it("unknown lesson returns null", () => {
    expect(computeNextItem(units, "u1", l1, undefined, "zzz")).toBeNull();
  });
});
