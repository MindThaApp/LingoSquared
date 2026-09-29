import { describe, expect, it } from "vitest";
import type { UnitSummary } from "@lingo/shared/api/types";
import { isCoreUnit, partitionUnits } from "./unitTracks";
import { findNextUnit } from "./nextLesson";

const u = (id: string, track?: "core" | "situation"): UnitSummary => ({
  id, title: id, order: 0, lesson_count: 1, completed_lesson_count: 0,
  section: "reading_writing", locked: false, checkpoint_passed: false,
  content_key: null, ...(track ? { track } : {}),
});

describe("unit tracks", () => {
  it("missing track is core", () => {
    expect(isCoreUnit(u("a"))).toBe(true);
    expect(isCoreUnit(u("b", "situation"))).toBe(false);
  });
  it("partitions", () => {
    const { core, situation } = partitionUnits([u("a"), u("s", "situation"), u("c", "core")]);
    expect(core.map((x) => x.id)).toEqual(["a", "c"]);
    expect(situation.map((x) => x.id)).toEqual(["s"]);
  });
  it("next unit skips situation units", () => {
    const units = [u("a"), u("s", "situation"), u("c")];
    expect(findNextUnit(units, "a")?.id).toBe("c");
    expect(findNextUnit(units, "s")).toBeNull();
  });
});
