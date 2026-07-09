// Last unit the learner opened per course, client-side only (same
// per-device localStorage precedent as levelPreferences.ts). Used purely
// to scroll the course path back to where they left off and mark it
// visually -- not a substitute for real per-unit completion data.
const PREFIX = "course-last-unit-";

export function getLastVisitedUnit(courseId: string): string | null {
  return localStorage.getItem(PREFIX + courseId);
}

export function setLastVisitedUnit(courseId: string, unitId: string): void {
  localStorage.setItem(PREFIX + courseId, unitId);
}
