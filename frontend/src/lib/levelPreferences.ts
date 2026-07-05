// Self-reported starting level per course, client-side only. Used to
// recommend a starting unit, not to unlock/skip anything server-side —
// reading/writing units are already freely navigable regardless of
// completion, so this only ever affects which unit gets highlighted as
// the recommended starting point.
export type SelfReportedLevel = "beginner" | "some_basics" | "conversational";

const STORAGE_PREFIX = "course-level-";

export function getLevelPreference(courseId: string): SelfReportedLevel | null {
  const value = localStorage.getItem(STORAGE_PREFIX + courseId);
  return value === "beginner" || value === "some_basics" || value === "conversational"
    ? value
    : null;
}

export function setLevelPreference(courseId: string, level: SelfReportedLevel): void {
  localStorage.setItem(STORAGE_PREFIX + courseId, level);
}

// Pick a recommended starting unit index (0-based) out of N reading/writing
// units, given a self-reported level. With few units this is necessarily
// coarse — honest guidance, not a precise placement.
export function recommendedUnitIndex(level: SelfReportedLevel, unitCount: number): number {
  if (unitCount <= 1) return 0;
  if (level === "beginner") return 0;
  if (level === "conversational") return unitCount - 1;
  return Math.floor((unitCount - 1) / 2);
}
