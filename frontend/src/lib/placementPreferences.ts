// Placement-test recommendation, client-side only (docs/PLACEMENT_TEST_SPEC.md
// §2.3). Same storage pattern as levelPreferences.ts's self-report -- MVP has
// ZERO backend persistence, so the result of a placement test is cached per
// course, per device in localStorage. This takes precedence over the
// self-report heuristic wherever both exist (see CourseUnitsPage.tsx); the
// growth step (docs/PLACEMENT_TEST_SPEC.md §3) will add a server-side
// GET /me/placement/{course_id} that this becomes a cache in front of.
export interface PlacementRecommendationPref {
  unitId: string;
  level: string;
  ts: number;
}

const STORAGE_PREFIX = "course-placement-";

export function getPlacementRecommendation(courseId: string): PlacementRecommendationPref | null {
  const raw = localStorage.getItem(STORAGE_PREFIX + courseId);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<PlacementRecommendationPref>;
    if (typeof parsed.unitId === "string" && typeof parsed.level === "string") {
      return { unitId: parsed.unitId, level: parsed.level, ts: typeof parsed.ts === "number" ? parsed.ts : 0 };
    }
  } catch {
    // Malformed/foreign value under this key -- treat as absent rather than
    // throwing and breaking CourseUnitsPage's highlight.
  }
  return null;
}

export function setPlacementRecommendation(
  courseId: string,
  rec: { unitId: string; level: string },
): void {
  const payload: PlacementRecommendationPref = { ...rec, ts: Date.now() };
  localStorage.setItem(STORAGE_PREFIX + courseId, JSON.stringify(payload));
}
