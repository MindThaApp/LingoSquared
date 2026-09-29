import type { LessonSummary, UnitSummary } from "@lingo/shared/api/types";

import { isCoreUnit } from "./unitTracks";

export type NextItem =
  | { kind: "lesson"; lessonId: string; unitId: string }
  | { kind: "checkpoint"; unitId: string };

// Pure: where "Next" should go after finishing `lessonId` in `currentUnitId`.
// - another lesson later in the same unit -> that lesson (by `order`)
// - last lesson of the unit -> the next unit in the same section (array order
//   as returned by the API): its first lesson, or its checkpoint if it has no
//   lessons
// - next unit locked / no next unit / data missing -> null (caller falls back
//   to "back to course"). `nextUnitLessons` may be undefined until fetched.
export function computeNextItem(
  units: UnitSummary[],
  currentUnitId: string,
  currentUnitLessons: LessonSummary[],
  nextUnitLessons: LessonSummary[] | undefined,
  lessonId: string,
): NextItem | null {
  const sorted = [...currentUnitLessons].sort((a, b) => a.order - b.order);
  const idx = sorted.findIndex((l) => l.id === lessonId);
  if (idx === -1) return null;
  if (idx < sorted.length - 1) {
    return { kind: "lesson", lessonId: sorted[idx + 1].id, unitId: currentUnitId };
  }
  const next = findNextUnit(units, currentUnitId);
  if (!next || next.locked) return null;
  if (nextUnitLessons === undefined) return null;
  const first = [...nextUnitLessons].sort((a, b) => a.order - b.order)[0];
  if (first) return { kind: "lesson", lessonId: first.id, unitId: next.id };
  return { kind: "checkpoint", unitId: next.id };
}

export function findNextUnit(units: UnitSummary[], currentUnitId: string): UnitSummary | null {
  const cur = units.find((u) => u.id === currentUnitId);
  if (!cur) return null;
  // Situation units are an optional shelf, never part of the "next" chain.
  if (!isCoreUnit(cur)) return null;
  const sameSection = units.filter((u) => u.section === cur.section && isCoreUnit(u));
  const i = sameSection.findIndex((u) => u.id === currentUnitId);
  return sameSection[i + 1] ?? null;
}
